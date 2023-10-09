
export function fuzzy_zero(f)
{
    return Math.abs(f) <= 0.00001;
}

export function fuzzy_compare(a, b)
{
    return Math.abs(a - b) * 100000 <= Math.min(Math.abs(a), Math.abs(b));
}

export function lerp(amount, p0, p1)
{
    return p0 * (1 - amount) + p1 * amount;
}


/**
 * \brief 2D point in space
 */
export class Point
{
    constructor(x, y)
    {
        if ( Array.isArray(x) )
        {
            [this.x, this.y] = x;
        }
        else if ( typeof x == "object" )
        {
            this.x = x.x;
            this.y = x.y;
        }
        else
        {
            this.x = x;
            this.y = y;
        }
    }

    static polar(angle, length)
    {
        return new Point(Math.cos(angle) * length, Math.sin(angle) * length);
    }

    lerp(amount, other)
    {
        return new Point(lerp(amount, this.x, other.x), lerp(amount, this.y, other.y));
    }

    add(...args)
    {
        let other = new Point(...args);
        other.x += this.x;
        other.y += this.y;
        return other;
    }

    sub(...args)
    {
        let other = new Point(...args);
        other.x = this.x - other.x;
        other.y = this.y - other.y;
        return other;
    }

    length()
    {
        return Math.hypot(this.x, this.y);
    }

    copy()
    {
        return new Point(this);
    }

    distance(...args)
    {
        return this.sub(...args).length();
    }

    mul(scalar)
    {
        return new Point(this.x * scalar, this.y * scalar);
    }

    div(scalar)
    {
        return new Point(this.x / scalar, this.y / scalar);
    }

    to_lottie()
    {
        return [this.x, this.y];
    }

    neg()
    {
        return new Point(-this.x, -this.y);
    }

    is_origin()
    {
        return this.x == 0 && this.y == 0;
    }

    add_polar(angle, length)
    {
        return new Point(this.x + Math.cos(angle) * length, this.y - Math.sin(angle) * length);
    }

    is_equal(other)
    {
        return other instanceof Point && fuzzy_compare(this.x, other.x) && fuzzy_compare(this.y, other.y);
    }

    static fromJSON(data)
    {
        return new Point(data);
    }

    toJSON()
    {
        return [this.x, this.y];
    }
}

/**
 * \brief 4x4 transform matrix and related operations
 */
export class Matrix
{
    constructor(elements)
    {
        this.elements = elements ?? Matrix.identity();
    }

    static identity()
    {
        let mat = new Float32Array(16);
        mat[0] = mat[5] = mat[10] = mat[15] = 1;
        return mat;
    }

    static rotation_z(angle)
    {
        let cos = Math.cos(angle);
        let sin = Math.sin(angle);
        let mat = new Float32Array(16);
        mat[0] = cos;
        mat[1] = -sin;
        mat[4] = sin;
        mat[5] = cos;

        mat[10] = mat[15] = 1;
        return mat;
    }

    static rotation_x(angle, axis)
    {
        let cos = Math.cos(angle);
        let sin = Math.sin(angle);
        let mat = new Float32Array(16);

        mat[5] = cos;
        mat[6] = -sin;
        mat[9] = sin;
        mat[10] = cos;

        mat[0] = mat[15] = 1;
        return mat;
    }

    static rotation_y(angle, axis)
    {
        let cos = Math.cos(angle);
        let sin = Math.sin(angle);
        let mat = new Float32Array(16);

        mat[0] = cos;
        mat[2] = sin;
        mat[8] = -sin;
        mat[10] = cos;

        mat[5] = mat[15] = 1;
        return mat;
    }

    static axis_skew(angle)
    {
        let mat = Matrix.identity();
        mat[4] = Math.tan(angle);
        return mat;
    }

    static scale_matrix(x, y, z = 1)
    {
        let mat = new Float32Array(16);
        mat[0] = x;
        mat[5] = y;
        mat[10] = z;
        mat[15] = 1;
        return mat;
    }

    static translation(x, y, z = 0)
    {
        let mat = this.identity();
        mat[12] = x;
        mat[13] = y;
        mat[14] = z;
        return mat;
    }

    mul(matrix)
    {
        if ( matrix instanceof Matrix )
            this._mul(matrix.elements);
        else
            this._mul(matrix);
    }

    _mul(matrix)
    {
        let mat = new Float32Array(16);

        for ( let row = 0; row < 4; row++ )
        {
            for ( let col = 0; col < 4; col++ )
            {
                let res = 0;
                for ( let i = 0; i < 4; i++ )
                    res += this.elements[row * 4 + i] * matrix[i * 4 + col];
                mat[row * 4 + col] = res;
            }
        }

        this.elements = mat;
    }

    map(x, y, z = 0)
    {
        return [
            x * this.elements[0] + y * this.elements[4] + z * this.elements[8] + this.elements[12],
            x * this.elements[1] + y * this.elements[5] + z * this.elements[9] + this.elements[13],
            x * this.elements[2] + y * this.elements[6] + z * this.elements[10] + this.elements[14],
        ]
    }

    rotate(angle)
    {
        this._mul(Matrix.rotation_z(angle));
        return this;
    }

    rotate_x(angle)
    {
        this._mul(Matrix.rotation_x(angle));
        return this;
    }

    rotate_y(angle)
    {
        this._mul(Matrix.rotation_y(angle));
        return this;
    }

    rotate_z(angle)
    {
        this._mul(Matrix.rotation_z(angle));
        return this;
    }

    translate(dx, dy, dz = 0)
    {
        this._mul(Matrix.translation(dx, dy, dz));
        return this;
    }

    scale(sx, sy, sz = 1)
    {
        this._mul(Matrix.scale_matrix(sx, sy, sz));
        return this;
    }

    skew(axis, angle)
    {
        this.rotate(-angle);
        this._mul(Matrix.axis_skew(-axis));
        this.rotate(angle);
    }

    inverted()
    {
        // plainly copied from mat4.js 'cause I CBA to implement it properly
        var a = this.elements;
        let a00 = a[0], a01 = a[1], a02 = a[2], a03 = a[3];
        let a10 = a[4], a11 = a[5], a12 = a[6], a13 = a[7];
        let a20 = a[8], a21 = a[9], a22 = a[10], a23 = a[11];
        let a30 = a[12], a31 = a[13], a32 = a[14], a33 = a[15];

        let b00 = a00 * a11 - a01 * a10;
        let b01 = a00 * a12 - a02 * a10;
        let b02 = a00 * a13 - a03 * a10;
        let b03 = a01 * a12 - a02 * a11;
        let b04 = a01 * a13 - a03 * a11;
        let b05 = a02 * a13 - a03 * a12;
        let b06 = a20 * a31 - a21 * a30;
        let b07 = a20 * a32 - a22 * a30;
        let b08 = a20 * a33 - a23 * a30;
        let b09 = a21 * a32 - a22 * a31;
        let b10 = a21 * a33 - a23 * a31;
        let b11 = a22 * a33 - a23 * a32;

        // Calculate the determinant
        let det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06;

        if ( !det )
            return null;

        det = 1.0 / det;


        let mat = new Float32Array(16);
        mat[0] = (a11 * b11 - a12 * b10 + a13 * b09) * det;
        mat[1] = (a02 * b10 - a01 * b11 - a03 * b09) * det;
        mat[2] = (a31 * b05 - a32 * b04 + a33 * b03) * det;
        mat[3] = (a22 * b04 - a21 * b05 - a23 * b03) * det;
        mat[4] = (a12 * b08 - a10 * b11 - a13 * b07) * det;
        mat[5] = (a00 * b11 - a02 * b08 + a03 * b07) * det;
        mat[6] = (a32 * b02 - a30 * b05 - a33 * b01) * det;
        mat[7] = (a20 * b05 - a22 * b02 + a23 * b01) * det;
        mat[8] = (a10 * b10 - a11 * b08 + a13 * b06) * det;
        mat[9] = (a01 * b08 - a00 * b10 - a03 * b06) * det;
        mat[10] = (a30 * b04 - a31 * b02 + a33 * b00) * det;
        mat[11] = (a21 * b02 - a20 * b04 - a23 * b00) * det;
        mat[12] = (a11 * b07 - a10 * b09 - a12 * b06) * det;
        mat[13] = (a00 * b09 - a01 * b07 + a02 * b06) * det;
        mat[14] = (a31 * b01 - a30 * b03 - a32 * b00) * det;
        mat[15] = (a20 * b03 - a21 * b01 + a22 * b00) * det;

        return new Matrix(mat);
    }

    to_canvas()
    {
        /*
            a b 0 0
            c d 0 0
            0 0 1 0
            e f 0 1
        */
        return [
            this.elements[0],
            this.elements[1],
            this.elements[4],
            this.elements[5],
            this.elements[12],
            this.elements[13]
        ];
    }
}


export class BoundingBox
{
    constructor(x, y, width, height)
    {
        this.left = x;
        this.top = y;
        this.width = width;
        this.height = height;
    }

    expand(margin)
    {
        this.left -= margin;
        this.top -= margin;
        this.width += 2 * margin;
        this.height += 2 * margin;
    }

    get right()
    {
        return this.left + this.width;
    }

    get bottom()
    {
        return this.top + this.height;
    }

    include_points(points)
    {
        let x = [];
        let y = [];

        if ( this.width >= 0 )
            x = [this.left, this.right];

        if ( this.height >= 0 )
            y = [this.top, this.bottom];

        for ( let p of points )
        {
            x.push(p.x);
            y.push(p.y);
        }

        this.left = Math.min(...x);
        this.top = Math.min(...y);
        this.width = Math.max(...x) - this.left;
        this.height = Math.max(...y) - this.top;

    }

    include(other)
    {
        if ( (other instanceof BoundingBox) && other.width < 0 )
            return;

        this.include_points(other.corners);
    }

    copy()
    {
        return new BoundingBox(this.left, this.top, this.width, this.height);
    }

    get center()
    {
        return new Point(
            this.left + this.width / 2,
            this.top + this.height / 2
        );
    }

    get corners()
    {
        return [
            new Point(this.left, this.top),
            new Point(this.right, this.top),
            new Point(this.right, this.bottom),
            new Point(this.left, this.bottom),
        ]
    }

    to_aabb()
    {
        return this;
    }
}

export class Polygon
{
    constructor(corners)
    {
        this.corners = corners;
    }

    expand()
    {
    }

    get center()
    {
        return this.corners.reduce((a, b) => a.add(b)).div(this.corners.length);
    }

    to_aabb()
    {
        let x = [];
        let y = [];

        for ( let p of this.corners )
        {
            x.push(p.x);
            y.push(p.y);
        }

        let left = Math.min(...x);
        let right = Math.max(...x);
        let top = Math.min(...y);
        let bottom = Math.max(...y);

        return new BoundingBox(left, top, right - left, bottom - top);
    }
}

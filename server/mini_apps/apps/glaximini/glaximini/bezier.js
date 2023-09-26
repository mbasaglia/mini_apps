import { fuzzy_zero, fuzzy_compare, BoundingBox, Point } from "./math.js"


export class BezierSegment
{
    constructor(k0, k1, k2, k3)
    {
        this.a = this._a(k0, k1, k2, k3);
        this.b = this._b(k0, k1, k2);
        this.c = this._c(k0, k1);
        this.d = this._d(k0);
        this.points = [k0, k1, k2, k3];
        this.length_data = [];
        this.length = -1;
    }

    get start()
    {
        return this.points[0];
    }

    get end()
    {
        return this.points[3];
    }

    lerp(factor, other)
    {
        return new BezierSegment(...this.points.map((v, i) => v.lerp(factor, other.points[i])));
    }

    point(t)
    {
        return this.a.mul(t).add(this.b).mul(t).add(this.c).mul(t).add(this.d);
    }

    value(t)
    {
        return this.point(t);
    }

    derivative(t)
    {
        return this.a.mul(3 * t).add(this.b.mul(2)).mul(t).add(this.c);
    }

    tangent_angle(t)
    {
        let p = this.derivative(t);
        return Math.atan2(p.y, p.x);
    }

    normal_angle(t)
    {
        let p = this.derivative(t);
        return Math.atan2(p.x, p.y);
    }

    _a(k0, k1, k2, k3)
    {
        return k0.neg().add(k1.mul(3)).add(k2.mul(-3)).add(k3);
    }

    _b(k0, k1, k2)
    {
        return k0.mul(3).add(k1.mul(-6)).add(k2.mul(3));
    }

    _c(k0, k1)
    {
        return k0.mul(-3).add(k1.mul(3));
    }

    _d(k0)
    {
        return k0;
    }

    inflection_points()
    {
        let denom = this.a.y * this.b.x - this.a.x * this.b.y;
        if ( fuzzy_zero(denom) )
            return [];

        let t_cusp = -0.5 * (this.a.y * this.c.x - this.a.x * this.c.y) / denom;

        let square = t_cusp * t_cusp - 1/3 * (this.b.y * this.c.x - this.b.x * this.c.y) / denom;

        if ( square < 0 )
            return [];

        let root = Math.sqrt(square);
        if ( fuzzy_zero(root) )
        {
            if ( t_cusp > 0 && t_cusp < 1 )
                return [t_cusp];
            return [];
        }

        return [t_cusp - root, t_cusp + root].filter(r => r > 0 && r < 1);
    }

    split(t)
    {
        if ( t == 0 )
            return [new BezierSegment(this.start, this.start, this.start, this.start), this];

        if ( t == 1 )
            return [this, new BezierSegment(this.end, this.end, this.end, this.end)];

        let p10 = this.points[0].lerp(t, this.points[1]);
        let p11 = this.points[1].lerp(t, this.points[2]);
        let p12 = this.points[2].lerp(t, this.points[3]);
        let p20 = p10.lerp(t, p11);
        let p21 = p11.lerp(t, p12);
        let p3 = p20.lerp(t, p21);

        return [
            new BezierSegment(this.points[0], p10, p20, p3),
            new BezierSegment(p3, p21, p12, this.points[3])
        ];
    }

    bounds()
    {
        return {
            x: this._extrema("x"),
            y: this._extrema("y"),
        };
    }

    bounding_box()
    {
        let bounds = this.bounds();

        return new BoundingBox(
            bounds.x.min,
            bounds.y.min,
            bounds.x.max - bounds.x.min,
            bounds.y.max - bounds.y.min,
        );
    }

    _extrema(comp)
    {
        let min = this.start[comp];
        let max = this.end[comp];

        if ( min > max )
            [min, max] = [max, min];

        // Derivative roots to find min/max
        for ( let t of quadratic_roots(3 * this.a[comp], 2 * this.b[comp], this.c[comp]) )
        {
            if ( t > 0 && t < 1 )
            {
                let val = this.point(t)[comp];
                if ( val < min )
                    min = val;
                else if ( val > max )
                    max = val;
            }
        }

        return {
            min: min,
            max: max
        };
    }

    ts_at_x(x)
    {
        return filter_roots(cubic_roots(this.a.x, this.b.x, this.c.x, this.d.x - x));
    }

    ys_at_x(x)
    {
        return this.ts_at_x(x).map(t => this.value(t).y);
    }
}


export class Bezier
{
    constructor(segments = [])
    {
        this.segments = segments;
    }

    add_segment(...points)
    {
        if ( points.length == 3 && this.segments.length > 0 )
            points.unshift(this.last_segment.end);

        this.segments.push(new BezierSegment(...points.map(p => new Point(p))));

    }

    close()
    {
        let [first, last, closed] = this._closed_impl();
        if ( first != null && !closed )
            this.segments.push(new BezierSegment(last, last, first, first));
    }

    _closed_impl()
    {
        if ( this.segments.length == 0 )
            return [null, null, false];

        let first = this.segments[0].start;
        let last = this.segments[this.segments.length - 1].end;
        return [first, last, first.is_equal(last)];
    }

    is_closed()
    {
        return this._closed_impl()[2];
    }

    get last_segment()
    {
        return this.segments[this.segments.length-1];
    }

    set last_segment(segment)
    {
        this.segments[this.segments.length-1] = segment;
    }


    segment(index)
    {
        return this.segments(index);
    }

    toJSON()
    {
        let points = [];
        if  ( this.segments.length > 0 )
        {
            points.push(this.segments[0].points[0]);
            for ( let seg of this.segments )
            {
                points.push(seg.points[1]);
                points.push(seg.points[2]);
                points.push(seg.points[3]);
            }
        }
        return points;
    }

    lerp(factor, other)
    {
        if ( factor <= 0 || other.segments.length != this.segments.length )
            return this;

        return new Bezier(this.segments.map((s, i) => s.lerp(factor, other.segments[i])));
    }

    static fromJSON(points)
    {
        let bez = new Bezier();

        if  ( points.length > 3 )
        {
            let last_p = Point.fromJSON(points[0]);
            for ( let i = 3; i < points.length; i += 3 )
            {
                let next_p = Point.fromJSON(points[i]);
                bez.segments.push(new BezierSegment(
                    last_p, Point.fromJSON(points[i-2]), Point.fromJSON(points[i-1]), next_p
                ));
                last_p = next_p;
            }
        }

        return bez;
    }

    bounding_box()
    {
        let bbox = new BoundingBox(-1, -1, -1, -1);

        if ( this.segments.length > 0 )
        {
            bbox = this.segments[0].bounding_box();
            for ( let seg of this.segments )
                bbox.include(seg.bounding_box());
        }

        return bbox;
    }

    contains_point(pos)
    {
        if ( this.segments.length == 0 )
            return false;

        let ys = [];
        for ( let seg of this.segments )
            ys = ys.concat(seg.ys_at_x(pos.x));

        if ( !this.is_closed() )
        {
            let p0 = this.segments[0].start;
            let p1 = this.last_segment.end;
            // TODO could just handle it as a linear segment, with a single solution
            ys = ys.concat((new BezierSegment(p0, p0, p1, p1)).ys_at_x(pos.x));
        }

        // Even odds
        let count = 0;
        for ( let y of ys )
            if ( y >= pos.y )
                count += 1;

        return count % 2;
    }

    draw_path(context)
    {
        if ( this.segments.length == 0 )
            return;

        context.moveTo(this.segments[0].start.x, this.segments[0].start.y);

        for ( let seg of this.segments )
            context.bezierCurveTo(
                seg.points[1].x, seg.points[1].y,
                seg.points[2].x, seg.points[2].y,
                seg.points[3].x, seg.points[3].y
            );

        if ( this.is_closed() )
            context.closePath();
    }

    dragged(offset)
    {
        return new Bezier(
            this.segments.map(s => new BezierSegment(
                ...s.points.map(p => p.add(offset))
            ))
        );
    }
}


// Filters roots so they are in [0, 1]
function filter_roots(roots)
{
    return roots.map(r => {
        if ( fuzzy_zero(r) )
            return 0;
        if ( fuzzy_compare(r, 1) )
            return 1;
        if ( 0 <= r && r <= 1 )
            return r;
        return null;
    }).filter(r => r !== null);
}

// Returns the real cube root of a value
function cuberoot(v)
{
    if ( v < 0 )
        return -Math.pow(-v, 1/3);
    return Math.pow(v, 1/3);
}

/*
 * Solves
 *      a x^3 + b x^2 + c x + d = 0
 * Returns only solutions in [0, 1]
 */
function cubic_roots(a, b, c, d)
{
    // If a is 0, it's a quadratic
    if ( fuzzy_zero(a) )
        return quadratic_roots(b, c, d);

    // Cardano's algorithm.
    b /= a;
    c /= a;
    d /= a;

    let p = (3*c - b * b) / 3;
    let p3 = p / 3;
    let q = (2 * b*b*b - 9 * b * c + 27 * d) / 27;
    let q2 = q / 2;
    let discriminant = q2 * q2 + p3 * p3 * p3;

    // and some variables we're going to use later on:

    // 3 real roots:
    if ( discriminant < 0)
    {
        let mp3  = -p / 3;
        let r = Math.sqrt(mp3*mp3*mp3);
        let t = -q / (2*r);
        let cosphi = t < -1 ? -1 : t > 1 ? 1 : t;
        let phi  = Math.acos(cosphi);
        let crtr = cuberoot(r);
        let t1   = 2 * crtr;
        let root1 = t1 * Math.cos(phi / 3) - b / 3;
        let root2 = t1 * Math.cos((phi + 2 * Math.PI) / 3) - b / 3;
        let root3 = t1 * Math.cos((phi + 4 * Math.PI) / 3) - b / 3;
        return [root1, root2, root3];
    }

    // 2 real roots
    if ( fuzzy_zero(discriminant) )
    {
        let u1 = q2 < 0 ? cuberoot(-q2) : -cuberoot(q2);
        let root1 = 2*u1 - b / 3;
        let root2 = -u1 - b / 3;
        return [root1, root2];
    }

    // 1 real root, 2 complex roots
    let sd = Math.sqrt(discriminant);
    let u1 = cuberoot(sd - q2);
    let v1 = cuberoot(sd + q2);
    return [u1 - v1 - b / 3];
}


/*
 * Solves
 *      a x^2 + b x + c = 0
 */
function quadratic_roots(a, b, c)
{
    // linear
    if ( fuzzy_zero(a) )
    {
        if ( fuzzy_zero(b) )
            return [];

        return [-c / b];
    }

    let s = b * b - 4 * a * c;

    // Complex roots
    if ( s < 0 )
        return [];

    let single_root = -b / (2 * a);

    // 1 root
    if ( fuzzy_zero(s) )
        return [single_root];

    let delta = Math.sqrt(s) / (2 * a);

    // 2 roots
    return [single_root - delta, single_root + delta];
}

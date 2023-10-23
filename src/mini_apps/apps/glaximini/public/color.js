export function hex_to_rgb(hex, scale=1)
{
    let rgb = [];

    for ( let i = 1; i < hex.length; i += 2 )
        rgb.push(parseInt(hex.substr(i, 2), 16) * scale);

    return rgb;
}

export function rgb_to_hex(rgb)
{
    let hex = "#";
    for ( let c of rgb )
        hex += component_to_hex(c);
    return hex;
}

export function lerp_rgb(factor, a, b)
{
    let c = [];
    for ( let i = 0; i < a.length; i++ )
        c.push(Math.round(a[i] * (1-factor) + b[i] * factor));
    return c;
}

export function lerp_hex(factor, a, b)
{
    return rgb_to_hex(lerp_rgb(factor, hex_to_rgb(a), hex_to_rgb(b)));
}

export function component_to_hex(v)
{
    return v.toString(16).padStart(2, "0");
}

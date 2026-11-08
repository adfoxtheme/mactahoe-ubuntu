// Dual Kawase downsample pass, used as a Cogl fragment snippet.
// Reads cogl_sampler0 and writes a half-resolution texture.

uniform vec2 inv_size; /* 1/width, 1/height of the source texture */
uniform float blur_radius; /* sample offset in source texels */

// Centre weighted 4, four diagonal taps weighted 1.
void main() {
    vec2 uv = cogl_tex_coord_in[0].st;
    float r = blur_radius;

    vec4 col  = texture2D(cogl_sampler0, uv) * 4.0;
    col += texture2D(cogl_sampler0, uv + vec2( r,  r) * inv_size);
    col += texture2D(cogl_sampler0, uv + vec2( r, -r) * inv_size);
    col += texture2D(cogl_sampler0, uv + vec2(-r,  r) * inv_size);
    col += texture2D(cogl_sampler0, uv + vec2(-r, -r) * inv_size);

    cogl_color_out = col / 8.0;
}

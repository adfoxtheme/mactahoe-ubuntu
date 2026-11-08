// Dual Kawase upsample pass (tent filter), used as a Cogl fragment snippet.
// Reads cogl_sampler0 and writes a texture twice its size.

uniform vec2 inv_size; /* 1/width, 1/height of the low-resolution source texture */
uniform float blur_radius; /* sample offset in source texels */

// Four axis taps weighted 2 and four diagonal taps weighted 1.
void main() {
    vec2 uv = cogl_tex_coord_in[0].st;
    float r = blur_radius;

    vec4 col;
    col  = texture2D(cogl_sampler0, uv + vec2(-r,  0.0) * inv_size) * 2.0;
    col += texture2D(cogl_sampler0, uv + vec2( r,  0.0) * inv_size) * 2.0;
    col += texture2D(cogl_sampler0, uv + vec2( 0.0, -r) * inv_size) * 2.0;
    col += texture2D(cogl_sampler0, uv + vec2( 0.0,  r) * inv_size) * 2.0;

    col += texture2D(cogl_sampler0, uv + vec2(-r, -r) * inv_size);
    col += texture2D(cogl_sampler0, uv + vec2( r, -r) * inv_size);
    col += texture2D(cogl_sampler0, uv + vec2(-r,  r) * inv_size);
    col += texture2D(cogl_sampler0, uv + vec2( r,  r) * inv_size);

    cogl_color_out = col / 12.0;
}

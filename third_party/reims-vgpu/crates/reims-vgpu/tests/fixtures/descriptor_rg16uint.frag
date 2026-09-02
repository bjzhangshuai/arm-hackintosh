#version 450
layout(set = 0, binding = 32) uniform utexture2D tex;
layout(set = 0, binding = 64) uniform sampler tex_sampler;
layout(location = 0) out vec4 color;
void main() {
    uvec2 a = texelFetch(usampler2D(tex, tex_sampler), ivec2(0, 0), 0).rg;
    uvec2 b = texelFetch(usampler2D(tex, tex_sampler), ivec2(1, 0), 0).rg;
    uvec2 c = texelFetch(usampler2D(tex, tex_sampler), ivec2(2, 0), 0).rg;
    bool exact = all(equal(a, uvec2(0, 1))) && all(equal(b, uvec2(255, 256)))
        && all(equal(c, uvec2(32768, 65535)));
    color = exact ? vec4(0.25, 0.5, 0.75, 1.0) : vec4(1, 0, 1, 1);
}

#version 450
layout(set = 0, binding = 32) uniform texture2D tex;
layout(set = 0, binding = 64) uniform sampler tex_sampler;
layout(location = 0) out vec4 color;
void main() { color = texture(sampler2D(tex, tex_sampler), vec2(0.5)); }

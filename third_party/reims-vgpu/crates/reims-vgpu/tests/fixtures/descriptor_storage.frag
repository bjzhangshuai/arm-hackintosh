#version 450
layout(set = 0, binding = 32, rgba16f) uniform readonly image2D tex;
layout(location = 0) out vec4 color;
void main() { color = imageLoad(tex, ivec2(0)); }

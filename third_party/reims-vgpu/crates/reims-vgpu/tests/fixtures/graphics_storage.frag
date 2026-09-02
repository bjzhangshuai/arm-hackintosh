#version 450
#ifndef FORMAT
#define FORMAT rgba16f
#endif
#ifdef UINT_IMAGE
layout(FORMAT, set=0, binding=163) uniform uimage2D destination;
#else
#ifdef FORMATLESS
layout(set=0, binding=163) writeonly uniform image2D destination;
#else
layout(FORMAT, set=0, binding=163) uniform image2D destination;
#endif
#endif
layout(location=0) out vec4 color;
void main() {
    color = vec4(0.25, 0.5, 0.75, 1);
    ivec2 p = ivec2(gl_FragCoord.xy);
    if (p.x == 0 || p.y == 0) return;
#ifdef UINT_IMAGE
    uvec4 value = uvec4(1000, 2000, 3000, 4000);
#else
    vec4 value = vec4(-2, 0.5, 3.25, 1);
#endif
#ifdef READ_SEED
    value += imageLoad(destination, p);
#endif
    imageStore(destination, p, value);
}

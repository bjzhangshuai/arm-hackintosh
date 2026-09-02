#version 450
#ifdef NARROW_TYPES
#extension GL_EXT_shader_explicit_arithmetic_types_float16 : require
#extension GL_EXT_shader_explicit_arithmetic_types_int16 : require
#endif
layout(input_attachment_index=0, set=0, binding=96) uniform subpassInput prior;
#ifdef FORMATLESS
layout(set=0, binding=163) writeonly uniform image2D destination;
#else
layout(rgba16f, set=0, binding=163) writeonly uniform image2D destination;
#endif
void main() {
    vec4 color = subpassLoad(prior);
    uvec2 coords = uvec2(gl_FragCoord.xy);
#ifdef NARROW_TYPES
    color = vec4(f16vec4(color));
    coords = uvec2(u16vec2(clamp(gl_FragCoord.xy, vec2(0), vec2(65535))));
#endif
    imageStore(destination, ivec2(coords), color);
}

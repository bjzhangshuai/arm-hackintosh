#version 450
layout(input_attachment_index = SECONDARY_SLOT, set = 0,
       binding = 96 + SECONDARY_SLOT) uniform subpassInput secondary_input;
#if READ_PRIMARY
layout(input_attachment_index = 0, set = 0, binding = 96) uniform subpassInput primary_input;
#endif
layout(location = 0) out vec4 color;
void main() {
#if READ_PRIMARY
    float r = subpassLoad(primary_input).r;
#else
    float r = 0.25;
#endif
    color = vec4(r, subpassLoad(secondary_input).g, 0.75, 1.0);
}

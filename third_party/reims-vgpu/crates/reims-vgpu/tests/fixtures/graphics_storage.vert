#version 450
#ifdef VERTEX_STORE
layout(rgba16f, set=0, binding=35) writeonly uniform image2D vertex_destination;
#endif
void main() {
    vec2 points[3] = vec2[3](vec2(-1,-1), vec2(3,-1), vec2(-1,3));
    gl_Position = vec4(points[gl_VertexIndex], 0, 1);
#ifdef VERTEX_STORE
    imageStore(vertex_destination, ivec2(gl_VertexIndex, 0), vec4(-2, 0.5, 3.25, 1));
#endif
}

/*
 * Fetch the Apple TSS ticket required by macOS iBootStage1's lpolrestore
 * command.  Build and run this helper only in the disposable Linux validation
 * VM; it deliberately has no USB/device access.
 *
 * cc -O2 -Wall -Wextra -o fetch-local-policy fetch_local_policy.c \
 *   $(pkg-config --cflags --libs libtatsu-1.0 libplist-2.0 openssl)
 */

#include <errno.h>
#include <inttypes.h>
#include <openssl/sha.h>
#include <plist/plist.h>
#include <libtatsu/tss.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const unsigned char empty_local_policy[] = {
    0x30, 0x14, 0x16, 0x04, 0x49, 0x4d, 0x34, 0x50,
    0x16, 0x04, 0x6c, 0x70, 0x6f, 0x6c, 0x16, 0x03,
    0x31, 0x2e, 0x30, 0x04, 0x01, 0x00,
};

/* iBootStage1's LocalPolicy BNCH comparison requires a 32-byte ApNonce. */
#define LOCAL_POLICY_APNONCE_SIZE 32

static int hex_nibble(char value)
{
    if (value >= '0' && value <= '9') {
        return value - '0';
    }
    if (value >= 'a' && value <= 'f') {
        return value - 'a' + 10;
    }
    if (value >= 'A' && value <= 'F') {
        return value - 'A' + 10;
    }
    return -1;
}

static unsigned char *decode_hex(const char *text, size_t *size)
{
    size_t text_size = strlen(text);
    unsigned char *bytes;
    size_t i;

    if (text_size == 0 || (text_size & 1) != 0) {
        return NULL;
    }
    bytes = malloc(text_size / 2);
    if (!bytes) {
        return NULL;
    }
    for (i = 0; i < text_size; i += 2) {
        int high = hex_nibble(text[i]);
        int low = hex_nibble(text[i + 1]);
        if (high < 0 || low < 0) {
            free(bytes);
            return NULL;
        }
        bytes[i / 2] = (unsigned char)((high << 4) | low);
    }
    *size = text_size / 2;
    return bytes;
}

static int write_bytes(const char *path, const void *data, size_t size)
{
    FILE *file = fopen(path, "wb");
    if (!file) {
        fprintf(stderr, "%s: %s\n", path, strerror(errno));
        return -1;
    }
    if (fwrite(data, 1, size, file) != size || fclose(file) != 0) {
        fprintf(stderr, "%s: failed to write complete output\n", path);
        return -1;
    }
    return 0;
}

static size_t der_length_size(size_t size)
{
    size_t bytes = 0;
    size_t value = size;

    if (size < 128) {
        return 1;
    }
    while (value) {
        bytes++;
        value >>= 8;
    }
    return 1 + bytes;
}

static unsigned char *der_write_header(unsigned char *out, unsigned char tag,
                                       size_t size)
{
    size_t bytes;
    size_t i;

    *out++ = tag;
    if (size < 128) {
        *out++ = (unsigned char)size;
        return out;
    }
    bytes = der_length_size(size) - 1;
    *out++ = (unsigned char)(0x80 | bytes);
    for (i = bytes; i > 0; i--) {
        *out++ = (unsigned char)(size >> ((i - 1) * 8));
    }
    return out;
}

static int write_personalized_local_policy(const char *path,
                                           const unsigned char *ticket,
                                           size_t ticket_size)
{
    static const unsigned char img4_magic[] = { 'I', 'M', 'G', '4' };
    size_t magic_size = 1 + der_length_size(sizeof(img4_magic)) +
                        sizeof(img4_magic);
    size_t ticket_element_size = 1 + der_length_size(ticket_size) + ticket_size;
    size_t content_size = magic_size + sizeof(empty_local_policy) +
                          ticket_element_size;
    size_t output_size = 1 + der_length_size(content_size) + content_size;
    unsigned char *output = malloc(output_size);
    unsigned char *cursor;
    int result;

    if (!output) {
        fprintf(stderr, "out of memory building personalized local policy\n");
        return -1;
    }
    cursor = der_write_header(output, 0x30, content_size);
    cursor = der_write_header(cursor, 0x16, sizeof(img4_magic));
    memcpy(cursor, img4_magic, sizeof(img4_magic));
    cursor += sizeof(img4_magic);
    memcpy(cursor, empty_local_policy, sizeof(empty_local_policy));
    cursor += sizeof(empty_local_policy);
    cursor = der_write_header(cursor, 0xa0, ticket_size);
    memcpy(cursor, ticket, ticket_size);
    cursor += ticket_size;
    if ((size_t)(cursor - output) != output_size) {
        fprintf(stderr, "internal DER size mismatch\n");
        free(output);
        return -1;
    }
    result = write_bytes(path, output, output_size);
    free(output);
    return result;
}

int main(int argc, char **argv)
{
    plist_t manifest = NULL;
    plist_t old_tss = NULL;
    plist_t identities;
    plist_t identity;
    plist_t parameters = NULL;
    plist_t local_policy = NULL;
    plist_t request = NULL;
    plist_t response = NULL;
    plist_format_t format;
    unsigned char *ap_nonce = NULL;
    size_t ap_nonce_size = 0;
    unsigned char *old_ticket = NULL;
    unsigned int old_ticket_size = 0;
    unsigned char *local_ticket = NULL;
    unsigned int local_ticket_size = 0;
    unsigned char digest[SHA384_DIGEST_LENGTH];
    uint64_t ecid;
    char *end = NULL;
    unsigned long identity_index;
    int result = 1;

    if (argc != 9) {
        fprintf(stderr,
                "usage: %s BUILD_MANIFEST IDENTITY_INDEX ECID APNONCE_HEX "
                "CURRENT_TSS OUTPUT_REQUEST OUTPUT_RESPONSE OUTPUT_IMG4\n",
                argv[0]);
        return 2;
    }

    identity_index = strtoul(argv[2], &end, 0);
    if (!end || *end != '\0') {
        fprintf(stderr, "invalid identity index: %s\n", argv[2]);
        goto out;
    }
    errno = 0;
    ecid = strtoull(argv[3], &end, 0);
    if (errno || !end || *end != '\0') {
        fprintf(stderr, "invalid ECID: %s\n", argv[3]);
        goto out;
    }
    ap_nonce = decode_hex(argv[4], &ap_nonce_size);
    if (!ap_nonce) {
        fprintf(stderr, "invalid ApNonce hex string\n");
        goto out;
    }
    if (ap_nonce_size != LOCAL_POLICY_APNONCE_SIZE) {
        fprintf(stderr,
                "LocalPolicy ApNonce must be exactly %u bytes, got %zu\n",
                LOCAL_POLICY_APNONCE_SIZE, ap_nonce_size);
        goto out;
    }
    if (plist_read_from_file(argv[1], &manifest, &format) != PLIST_ERR_SUCCESS ||
        !manifest) {
        fprintf(stderr, "failed to read BuildManifest: %s\n", argv[1]);
        goto out;
    }
    if (plist_read_from_file(argv[5], &old_tss, &format) != PLIST_ERR_SUCCESS ||
        !old_tss) {
        fprintf(stderr, "failed to read current TSS response: %s\n", argv[5]);
        goto out;
    }
    identities = plist_dict_get_item(manifest, "BuildIdentities");
    if (!identities || plist_get_node_type(identities) != PLIST_ARRAY ||
        identity_index >= plist_array_get_size(identities)) {
        fprintf(stderr, "BuildIdentity index %lu is out of range\n", identity_index);
        goto out;
    }
    identity = plist_array_get_item(identities, (uint32_t)identity_index);

    parameters = plist_new_dict();
    plist_dict_set_item(parameters, "ApECID", plist_new_uint(ecid));
    plist_dict_set_item(parameters, "Ap,LocalBoot", plist_new_bool(0));
    plist_dict_set_item(parameters, "ApNonce",
                        plist_new_data((const char *)ap_nonce, ap_nonce_size));
    plist_dict_set_item(parameters, "ApProductionMode", plist_new_bool(1));
    plist_dict_set_item(parameters, "ApSecurityMode", plist_new_bool(1));
    plist_dict_set_item(parameters, "ApSupportsImg4", plist_new_bool(1));
    if (tss_parameters_add_from_manifest(parameters, identity, true) < 0) {
        fprintf(stderr, "failed to copy BuildIdentity parameters\n");
        goto out;
    }

    SHA384(empty_local_policy, sizeof(empty_local_policy), digest);
    local_policy = plist_new_dict();
    plist_dict_set_item(local_policy, "Digest",
                        plist_new_data((const char *)digest, sizeof(digest)));
    plist_dict_set_item(local_policy, "Trusted", plist_new_bool(1));
    plist_dict_set_item(parameters, "Ap,LocalPolicy", local_policy);
    local_policy = NULL;

    if (tss_response_get_ap_img4_ticket(old_tss, &old_ticket,
                                        &old_ticket_size) < 0 ||
        !old_ticket || old_ticket_size == 0) {
        fprintf(stderr, "current TSS response has no ApImg4Ticket\n");
        goto out;
    }
    SHA384(old_ticket, old_ticket_size, digest);
    plist_dict_set_item(parameters, "Ap,NextStageIM4MHash",
                        plist_new_data((const char *)digest, sizeof(digest)));

    request = tss_request_new(NULL);
    if (!request || tss_request_add_local_policy_tags(request, parameters) < 0) {
        fprintf(stderr, "failed to construct local-policy TSS request\n");
        goto out;
    }
    if (plist_write_to_file(request, argv[6], PLIST_FORMAT_XML,
                            PLIST_OPT_NONE) != PLIST_ERR_SUCCESS) {
        fprintf(stderr, "failed to write request audit file: %s\n", argv[6]);
        goto out;
    }

    response = tss_request_send(request, NULL);
    if (!response || !plist_dict_get_item(response, "ApImg4Ticket")) {
        fprintf(stderr, "Apple TSS did not return an ApImg4Ticket\n");
        goto out;
    }
    if (plist_write_to_file(response, argv[7], PLIST_FORMAT_XML,
                            PLIST_OPT_NONE) != PLIST_ERR_SUCCESS) {
        fprintf(stderr, "failed to write TSS response: %s\n", argv[7]);
        goto out;
    }
    if (write_bytes("Ap.LocalPolicy.empty.im4p", empty_local_policy,
                    sizeof(empty_local_policy)) < 0) {
        goto out;
    }
    if (tss_response_get_ap_img4_ticket(response, &local_ticket,
                                        &local_ticket_size) < 0 ||
        !local_ticket || local_ticket_size == 0) {
        fprintf(stderr, "local-policy response has no usable ApImg4Ticket\n");
        goto out;
    }
    if (write_personalized_local_policy(argv[8], local_ticket,
                                        local_ticket_size) < 0) {
        goto out;
    }

    printf("Apple signed local policy: ECID=0x%016" PRIx64
           " identity=%lu nonce_bytes=%zu previous_ticket_bytes=%u "
           "local_ticket_bytes=%u\n",
           ecid, identity_index, ap_nonce_size, old_ticket_size,
           local_ticket_size);
    result = 0;

out:
    free(ap_nonce);
    free(old_ticket);
    free(local_ticket);
    plist_free(response);
    plist_free(request);
    plist_free(local_policy);
    plist_free(parameters);
    plist_free(old_tss);
    plist_free(manifest);
    return result;
}

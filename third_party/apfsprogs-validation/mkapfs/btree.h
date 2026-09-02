/*
 * Copyright (C) 2019 Ernesto A. Fernández <ernesto.mnd.fernandez@gmail.com>
 */

#ifndef _BTREE_H
#define _BTREE_H

#include <apfs/types.h>

extern void make_empty_btree_root(u64 bno, u64 oid, u32 subtype);
/* volume_index == -1 selects the container object map. */
extern void make_omap_btree(u64 bno, int volume_index);
extern void make_cat_root(u64 bno, u64 oid);

#endif	/* _BTREE_H */

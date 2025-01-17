/*
Copyright 2022 University of Applied Sciences Augsburg

This file is part of Augsburg-Traceroute.

Augsburg-Traceroute is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

Augsburg-Traceroute is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
Augsburg-Traceroute. If not, see <https://www.gnu.org/licenses/>.
*/

#ifndef CURSOR_H
#define CURSOR_H

#include <linux/bpf.h>
#include <linux/ip.h>

struct cursor {
    struct __sk_buff *skb;
    void *pos;
};

static long cursor_start(struct cursor *cursor)
{
    return cursor->skb->data;
}

static long cursor_end(struct cursor *cursor)
{
    return cursor->skb->data_end;
}

static void cursor_reset(struct cursor *cursor)
{
    cursor->pos = (void *)cursor_start(cursor);
}

static void cursor_init(struct cursor *cursor, struct __sk_buff *skb)
{
    cursor->skb = skb;
    cursor_reset(cursor);
}

static void cursor_clone(struct cursor *original, struct cursor *clone)
{
    *clone = *original;
}


#define PARSE(cursor, hdr)                                                     \
    ({                                                                         \
        int __ret = -1;                                                        \
        typeof(*(hdr)) __tmp = (cursor)->pos;                                  \
        if ((long)(cursor)->pos + sizeof(*__tmp) <= cursor_end(cursor)) {      \
            (cursor)->pos = __tmp + 1;                                         \
            *(hdr) = __tmp;                                                    \
            __ret = 0;                                                         \
        }                                                                      \
        __ret;                                                                 \
    })

// Parses the IP header including any following options.
static int PARSE_IP(struct cursor *cursor, struct iphdr **hdr)
{
    if (PARSE(cursor, hdr) < 0)
        return -1;

    long new_pos = (long)(*hdr) + (**hdr).ihl * 4;
    if (new_pos <= cursor_end(cursor)) {
        cursor->pos = (void *)new_pos;
        return 0;
    }

    return -1;
}
#endif

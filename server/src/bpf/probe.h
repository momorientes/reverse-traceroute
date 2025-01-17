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

#ifndef PROBE_H
#define PROBE_H

#include "cursor.h"
#include "internal.h"
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/types.h>

#define SOURCE_PORT bpf_htons(1021)

struct probe {
    __be16 flow;
    __be16 identifier;
};

struct probe_args {
    __u8 ttl;
    __u8 proto;

    struct probe probe;
};

typedef enum {
    ERR_NONE = 0x00,
    ERR_TTL = 0x01,
    ERR_PROTO = 0x02,
    ERR_FLOW = 0x03,
} probe_error;

INTERNAL int probe_create(struct cursor *cursor, struct probe_args *args,
                          struct ethhdr **eth, struct iphdr **ip);
INTERNAL int probe_match(struct cursor *cursor, __u8 proto, __u8 is_request);

#endif

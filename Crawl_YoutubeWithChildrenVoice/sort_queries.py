#!/usr/bin/env python3
# -*- coding: utf-8 -*-

with open('queries.txt', 'r', encoding='utf-8') as f:
    queries = [line.strip() for line in f if line.strip()]

# Remove duplicates and sort by length (shortest first)
queries = sorted(set(queries), key=len)

with open('queries.txt', 'w', encoding='utf-8') as f:
    for query in queries:
        f.write(query + '\n')
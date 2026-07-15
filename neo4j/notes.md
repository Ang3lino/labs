# Neo4j / Cypher Notes

## Mental Model: Relational → Graph

| Relational | Neo4j |
|------------|-------|
| Table | Node Label (`:Battle`, `:House`) |
| Row | Node |
| Column / Field | Property Key |
| Foreign Key / JOIN | Relationship |
| Junction table column | Relationship property |
| `DESC table` | `MATCH (n:Label) RETURN keys(n) LIMIT 1` |
| ERD / EER diagram | `CALL db.schema.visualization()` |

Key difference: **no enforced schema**. Two nodes with the same label can have completely different properties. No `ALTER TABLE ADD COLUMN` needed.

## Inspecting the Schema

```cypher
-- EER equivalent (visual graph of labels + relationship types)
CALL db.schema.visualization()

-- All node labels and counts
MATCH (n) RETURN labels(n)[0] AS label, count(*) ORDER BY count(*) DESC

-- All property keys in the DB
CALL db.propertyKeys()

-- Properties on a specific label ("DESC table")
MATCH (b:Battle) RETURN keys(b) LIMIT 1

-- Properties with sample values
MATCH (b:Battle) RETURN b LIMIT 1

-- Properties on a relationship type
MATCH ()-[r:ATTACKER]->() RETURN keys(r) LIMIT 1

-- All relationship types and counts
MATCH ()-[r]->() RETURN type(r) AS type, count(*) ORDER BY count(*) DESC
```

## Property Keys

A property key = a field/column. Lives on **both nodes and relationships**.

- Node property: `b.attacker_size` — data stored on the node itself
- Relationship property: `r.outcome` — data stored on the edge (like a junction table column)

To know where a property lives, check `keys()` on nodes vs relationships. There's no shortcut — you need the pattern to inspect relationship props.

## Querying Basics

```cypher
-- Direct relationship
MATCH (a:House)-[r]->(b:Battle) RETURN a, r, b

-- Chain (multi-hop, like joining through intermediate tables)
MATCH (a:House)-[r1]->(b:Battle), (b)-[r2]->(c:Location)
RETURN a.name, b.name, c.name

-- Shortest path (up to N hops)
MATCH p=shortestPath((a:House{name:"Stark"})-[*..5]-(b:House{name:"Lannister"}))
RETURN p

-- OR on relationship types (colon, not curly braces)
MATCH (p:Person)-[r:ATTACKER_COMMANDER|DEFENDER_COMMANDER]->(b:Battle)
RETURN p.name, type(r), b.name
```

## Aggregation (GROUP BY / HAVING)

No `GROUP BY` keyword. Aggregation is implicit from non-aggregated fields.

```cypher
-- Implicit grouping: h.name is the group key, count is the aggregate
MATCH (h:House)-[r]->(b:Battle)
RETURN h.name, count(b)

-- HAVING equivalent: WHERE after WITH
MATCH (h:House)-[r]->(b:Battle)
WITH h.name AS name, count(b) AS fights
WHERE fights > 5
RETURN name, fights
```

**Rules:**
- `RETURN` without aggregation = all rows (no grouping)
- `RETURN` with aggregation = non-aggregated fields become group keys
- `RETURN DISTINCT` = deduplicate
- `HAVING` = `WHERE` placed after `WITH`

## WITH Clause

Think of it as a CTE / subquery boundary. **Required when:**

1. Filtering on an aggregated value (HAVING)
2. Referencing a computed alias in another expression
3. Avoiding writing the same expression twice (compute once, reuse)
4. Piping between multiple MATCH stages

```cypher
-- Compute once, reuse (avoids bugs from duplicated expressions)
MATCH (b:Battle)
WITH b.name AS name,
     coalesce(b.attacker_size, 0) + coalesce(b.defender_size, 0) AS total
WHERE total > 50000
RETURN name, total
ORDER BY total DESC
```

Safe default: always `WITH` then `RETURN`. Never wrong.

## CASE WHEN + Casting

```cypher
MATCH (h:House)-[r:ATTACKER]->(b:Battle)
RETURN h.name,
       sum(CASE WHEN r.outcome = "win" THEN 1 ELSE 0 END) AS wins,
       count(DISTINCT b) AS fights,
       toFloat(wins) / fights AS ratio  -- ERROR: can't reference alias in same RETURN
```

Fix: use `WITH` to compute first, then `RETURN`:

```cypher
MATCH (h:House)-[r]->(b:Battle)
WITH h.name AS name,
     sum(CASE WHEN r.outcome = "win" THEN 1 ELSE 0 END) AS wins,
     count(DISTINCT b) AS fights
RETURN name, wins, fights, toFloat(wins) / fights AS ratio
ORDER BY wins DESC, ratio DESC
```

Cast functions: `toInteger()`, `toFloat()`, `toString()`.

## Showing Relationship Properties Explicitly

The browser graph view hides relationship properties. To see them as columns:

```cypher
MATCH (h:House)-[r]->(b:Battle)
WHERE b.name = "The Red Wedding"
RETURN h.name, type(r) AS rel_type, properties(r) AS rel_props, b.name
```

`properties(x)` = key-value map. `keys(x)` = just the field names.

## Neo4j Browser Shortcuts

| Action | Windows/Linux |
|--------|---------------|
| Run query | `Ctrl + Enter` |
| New line | `Shift + Enter` |
| History prev/next | `Ctrl + ↑/↓` |
| Focus editor | `/` |
| All shortcuts | `F1` |
| Clear frames | type `:clear` |
| Help | type `:help keys` |

No "cells" concept — each execution creates a result frame below. Previous frames persist until `:clear`.

## File Conventions

- Cypher files: `.cypher` extension (not `.sql`)
- Neo4j loads CSVs from `/var/lib/neo4j/import/` inside the container
- Separate Cypher statements with `;` when running via `cypher-shell --file`

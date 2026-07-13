# Cypher Cheatsheet

## Database

```cypher
-- Show current database
CALL db.info() YIELD name

-- List all databases
SHOW DATABASES
```

## Nodes

```cypher
-- List all node labels and counts
MATCH (n) RETURN labels(n)[0] AS label, count(*) ORDER BY count(*) DESC

-- List all nodes of a label
MATCH (n:Battle) RETURN n LIMIT 10

-- Count all nodes
MATCH (n) RETURN count(n)
```

## Relationships

```cypher
-- List all relationship types and counts
MATCH ()-[r]->() RETURN type(r) AS type, count(*) ORDER BY count(*) DESC

-- Show relationships for a node
MATCH (h:House{name:"Lannister"})-[r]->(b) RETURN type(r), b.name

-- All relationships (visual in browser)
MATCH p=()-[]-() RETURN p LIMIT 25
```

## Schema

```cypher
-- Show all constraints
SHOW CONSTRAINTS

-- Show all indexes
SHOW INDEXES

-- Schema visualization
CALL db.schema.visualization()
```

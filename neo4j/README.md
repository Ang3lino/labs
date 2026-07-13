# Neo4j - Game of Thrones Battles

## Prerequisites

- Docker / Rancher Desktop

## Run

```bash
docker compose up -d
```

## Access

- Browser: http://localhost:7474
- Credentials: `neo4j` / `changeme`
- Bolt: `bolt://localhost:7687`

## Load data

```bash
docker compose exec -T neo4j cypher-shell -u neo4j -p changeme --file /var/lib/neo4j/import/init.sql
```

## Stop

```bash
docker compose down
```

To wipe data: `docker compose down -v`

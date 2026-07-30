MATCH (n)
RETURN labels(n)[0] AS label, count(*)
ORDER BY count(*) DESC;

CALL db.schema.visualization();

MATCH (h:House)-[r]->(b:Battle)
RETURN h, r, b;

// name: "The Red Wedding"
MATCH (h:House)-[r]->(b:Battle)
WHERE b.name = "The Red Wedding"
RETURN h, r, b;

MATCH (h:House)-[r:ATTACKER]->(b:Battle)
RETURN h.name, sum(
    CASE
      WHEN r.outcome = "win" THEN 1
      ELSE 0
    END) AS wins
ORDER BY wins DESC;

MATCH (h:House)-[r]->(b:Battle)
WHERE h.name = "Baratheon"
RETURN h, r, b;

MATCH (h:House)-[r]->(b:Battle)
WHERE h.name = "Baratheon"
RETURN h.name, COUNT(DISTINCT b);

MATCH (h:House)-[r]->(b:Battle)
WHERE h.name = "Baratheon"
WITH
  h.name AS mname,
  sum(
    CASE
      WHEN r.outcome = "win" THEN 1
      ELSE 0
    END) AS wins,
  count(DISTINCT b) AS fights
RETURN mname, wins, fights, toFloat(wins) / fights AS ratio;

MATCH (h:House)-[r]->(b:Battle)
WITH
  h.name AS mname,
  sum(
    CASE
      WHEN r.outcome = "win" THEN 1
      ELSE 0
    END) AS wins,
  count(DISTINCT b) AS fights
RETURN mname, wins, fights, toFloat(wins) / fights AS win_ratio
ORDER BY wins DESC;

// Return the House who won the most battles and its win rate which is: |wins| /|fights| and how many battles it has won.
MATCH (h:House)-[r]->(b:Battle)
WITH
  h.name AS mname,
  sum(
    CASE
      WHEN r.outcome = "win" THEN 1
      ELSE 0
    END) AS wins,
  count(DISTINCT b) AS fights
RETURN mname, toFloat(wins) / fights AS win_ratio, wins
ORDER BY wins DESC
LIMIT 1;

// Return the House who won the most battles and its win rate in percentage which is: |wins| /|fights| and how many battles it has won
MATCH (h:House)-[r]->(b:Battle)
WITH
  h.name AS mname,
  sum(
    CASE
      WHEN r.outcome = "win" THEN 1
      ELSE 0
    END) AS wins,
  count(DISTINCT b) AS fights
RETURN mname, 100 * toFloat(wins) / fights AS win_ratio, wins
ORDER BY wins DESC
LIMIT 1;

// Return all the battles house Lannister has lost
MATCH (h:house)-[r]->(b:battle)
WHERE h.name = "lannister" AND r.outcome = "loss"
RETURN b.name;

// Return how many battles the Lannisters lost.
MATCH (h:house)-[r]->(b:battle)
WHERE h.name = "lannister" AND r.outcome = "loss"
RETURN count(*);

// Return all the enemies of House Lannister- an enemy is considered a house which fought against House Lannister.
MATCH (l:House {name: "Lannister"})-[r1]->(b:Battle)<-[r2]-(h:House)
RETURN b.name, h.name;

MATCH (l:House {name: "Lannister"})-[r1]->(b:Battle)<-[r2]-(h:House)
RETURN DISTINCT h.name;

// Return all the battles where more than 50000 people were involved
MATCH (p:Person)
RETURN count(*);
MATCH (p:Person)-[r]->(b:Battle)
RETURN r;

MATCH (p:Person)-[r]->(b:Battle)
WITH b.name AS bname, count(*) AS people_involved
// WHERE people_involved > 50000
RETURN bname, people_involved
ORDER BY people_involved DESC;

MATCH (b:Battle)
RETURN keys(b)
LIMIT 1; //  What's on the node?
//["major_death", "major_capture", "battle_type", "name", "attacker_size", "defender_size", "year", "summer"]

MATCH ()-[r:ATTACKER]->()
RETURN keys(r)
LIMIT 1; //  What's on the relationship?
MATCH (b:Battle)
RETURN b;

MATCH (b:Battle)
// WHERE (b.attacker_size + b.defender_size) > 50000
RETURN b.name, b.attacker_size + b.defender_size;

MATCH (b:Battle)
WHERE (b.attacker_size + b.defender_size) > 50000
RETURN b.name, b.attacker_size + b.defender_size;

// Return who commanded the most battles
MATCH (p:Person)-[r:ATTACKER_COMMANDER|DEFENDER_COMMANDER]->(b:Battle)
WITH p.name AS name, count(*) AS mcount
RETURN name, mcount
ORDER BY mcount DESC;


MATCH (n) RETURN labels(n)[0] AS label, count(*) ORDER BY count(*) DESC;

CALL db.schema.visualization();

MATCH (h: House) -[r]-> (b:Battle) RETURN h, r, b;

-- name: "The Red Wedding"
MATCH (h: House) -[r]-> (b:Battle) 
    WHERE b.name = "The Red Wedding"
    RETURN h, r, b;

MATCH (h:House)-[r:ATTACKER]->(b:Battle)
RETURN h.name,
       sum(CASE WHEN r.outcome = "win" THEN 1 ELSE 0 END) AS wins
ORDER BY wins DESC;

MATCH (h: House) -[r]-> (b:Battle) 
    WHERE h.name = "Baratheon"
    RETURN h, r, b;

MATCH (h: House) -[r]-> (b:Battle) 
    WHERE h.name = "Baratheon"
    RETURN h.name, COUNT(DISTINCT b);

MATCH (h: House) -[r]-> (b:Battle) 
    WHERE h.name = "Baratheon"
    RETURN h.name
        , sum(CASE WHEN r.outcome = "win" THEN 1 ELSE 0 END) AS wins
        , count(DISTINCT b) AS fights
        , wins / fights AS ratio
;

MATCH (h: House) -[r]-> (b:Battle) 
    WHERE h.name = "Baratheon"
    WITH h.name AS mname
        , sum(CASE WHEN r.outcome = "win" THEN 1 ELSE 0 END) AS wins
        , count(DISTINCT b) AS fights
    RETURN mname, wins, fights, toFloat(wins)/fights AS ratio
;

MATCH (h: House) -[r]-> (b:Battle) 
    WITH h.name AS mname
        , sum(CASE WHEN r.outcome = "win" THEN 1 ELSE 0 END) AS wins
        , count(DISTINCT b) AS fights
    RETURN mname
        , wins
        , fights
        , toFloat(wins)/fights AS win_ratio
    ORDER BY wins DESC
;


-- Return the House who won the most battles and its win rate which is: |wins| /|fights| and how many battles it has won.
MATCH (h: House) -[r]-> (b:Battle) 
    WITH h.name AS mname
        , sum(CASE WHEN r.outcome = "win" THEN 1 ELSE 0 END) AS wins
        , count(DISTINCT b) AS fights
    RETURN mname
        , toFloat(wins)/fights AS win_ratio
        , wins
    ORDER BY wins DESC
    LIMIT 1
;
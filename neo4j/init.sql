LOAD CSV WITH HEADERS FROM 
"file:///battles.csv" as row
//merge node labeled Battle 
MERGE (b:Battle{name:row.name})
ON CREATE SET b.year = toInteger(row.year),
              b.summer = row.summer,
              b.major_death = row.major_death,
              b.major_capture = row.major_capture,
              b.note = row.note,
              b.battle_type = row.battle_type,
              b.attacker_size = toInteger(row.attacker_size),
              b.defender_size = toInteger(row.defender_size);

LOAD CSV WITH HEADERS FROM 
"file:///battles.csv" as row
WITH row,
case when row.attacker_outcome = "win" THEN "loss" ELSE "win" END as defender_outcome
MATCH (b:Battle{name:row.name})
MERGE (attacker1:House{name:row.attacker_1}) 
MERGE (attacker1)-[a1:ATTACKER]->(b) 
ON CREATE SET a1.outcome = row.attacker_outcome
FOREACH
  (ignoreMe IN CASE WHEN row.defender_1 is not null THEN [1] ELSE [] END | 
    MERGE (defender1:House{name:row.defender_1})
    MERGE (defender1)-[d1:DEFENDER]->(b)
    ON CREATE SET d1.outcome = defender_outcome)
FOREACH
  (ignoreMe IN CASE WHEN row.defender_2 is not null THEN [1] ELSE [] END | 
    MERGE (defender2:House{name:row.defender_2})
    MERGE (defender2)-[d2:DEFENDER]->(b)
    ON CREATE SET d2.outcome = defender_outcome)
FOREACH
  (ignoreMe IN CASE WHEN row.attacker_2 is not null THEN [1] ELSE [] END | 
    MERGE (attacker2:House{name:row.attacker_2})
    MERGE (attacker2)-[a2:ATTACKER]->(b)
    ON CREATE SET a2.outcome = row.attacker_outcome)
FOREACH
  (ignoreMe IN CASE WHEN row.attacker_3 is not null THEN [1] ELSE [] END | 
    MERGE (attacker2:House{name:row.attacker_3})
    MERGE (attacker3)-[a3:ATTACKER]->(b)
    ON CREATE SET a3.outcome = row.attacker_outcome)
FOREACH
  (ignoreMe IN CASE WHEN row.attacker_4 is not null THEN [1] ELSE [] END | 
    MERGE (attacker4:House{name:row.attacker_4})
    MERGE (attacker4)-[a4:ATTACKER]->(b)
    ON CREATE SET a4.outcome = row.attacker_outcome);

LOAD CSV WITH HEADERS FROM 
"file:///battles.csv"as row
MATCH (b:Battle{name:row.name})
// We use coalesce, so that null values are replaced with "Unknown" 
MERGE (location:Location{name:coalesce(row.location,"Unknown")})
MERGE (b)-[:IS_IN]->(location)
MERGE (region:Region{name:row.region})
MERGE (location)-[:IS_IN]->(region);

LOAD CSV WITH HEADERS FROM 
"file:///battles.csv" as row
WITH row,
     split(row.attacker_commander,",") as att_commanders,
     split(row.defender_commander,",") as def_commanders,
     split(row.attacker_king,"/") as att_kings,
     split(row.defender_king,"/") as def_kings,
     row.attacker_outcome as att_outcome,
     CASE when row.attacker_outcome = "win" THEN "loss" 
     ELSE "win" END as def_outcome
MATCH (b:Battle{name:row.name})
UNWIND att_commanders as att_commander
MERGE (p:Person{name:trim(att_commander)})
MERGE (p)-[ac:ATTACKER_COMMANDER]->(b)
ON CREATE SET ac.outcome=att_outcome
WITH b,def_commanders,def_kings,att_kings,att_outcome,def_outcome,count(*) as c1
UNWIND def_commanders as def_commander
MERGE (p:Person{name:trim(def_commander)})
MERGE (p)-[dc:DEFENDER_COMMANDER]->(b)
ON CREATE SET dc.outcome = def_outcome
WITH b,def_kings,att_kings,att_outcome,def_outcome,count(*) as c2
UNWIND def_kings as def_king
MERGE (p:Person{name:trim(def_king)})
MERGE (p)-[dk:DEFENDER_KING]->(b)
ON CREATE SET dk.outcome = def_outcome
WITH b,att_kings,att_outcome,count(*) as c3
UNWIND att_kings as att_king
MERGE (p:Person{name:trim(att_king)})
MERGE (p)-[ak:ATTACKER_KING]->(b)
ON CREATE SET ak.outcome = att_outcome;
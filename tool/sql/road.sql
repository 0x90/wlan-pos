SET CLIENT_ENCODING TO UTF8;
BEGIN;
CREATE TABLE "gis_schema"."road" (gid serial PRIMARY KEY,
"mapid" varchar(8),
"id" varchar(13),
"kind" varchar(23),
"width" varchar(3),
"direction" varchar(1),
"snodeid" varchar(13),
"enodeid" varchar(13),
"pathclass" varchar(2),
"length" varchar(8),
"name" varchar(254));
SELECT AddGeometryColumn('gis_schema','road','the_geom','4326','MULTILINESTRING',2);

INSERT INTO "gis_schema"."road" ("mapid","id","kind","width","direction","snodeid","enodeid","pathclass","length","name",the_geom) 
SELECT r.mapid, rn.route_id, r.kind, r.width, r.direction, r.snodeid, r.enodeid, r.pathclass, r.length, rn.pathname, r.the_geom
 FROM gis_schema.r_namebeijing rn, gis_schema.rbeijing r, gis_schema.r_lnamebeijing rln
WHERE rn.language = '1' AND rn.route_id = rln.route_id AND r.id = rln.id;
END;

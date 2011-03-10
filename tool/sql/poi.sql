SET CLIENT_ENCODING TO UTF8;
BEGIN;
CREATE TABLE "gis_schema"."poi" (gid serial PRIMARY KEY,
"mapid" varchar(8),
"kind" varchar(4),
"telephone" varchar(15),
"poi_id" varchar(13),
"linkid" varchar(13),
"side" varchar(1),
"name" varchar(254),
"PY" varchar(254));
SELECT AddGeometryColumn('gis_schema','poi','the_geom','4326','POINT',2);

INSERT INTO gis_schema.poi ("mapid","kind","telephone","poi_id","linkid","side","name","PY",the_geom) 
SELECT p.mapid, p.kind, p.telephone, p.poi_id, p.linkid, p.side, fn.name, fn.py, p.the_geom 
FROM gis_schema.pbeijing p, gis_schema.fnamebeijing fn 
WHERE fn.featid = p.poi_id AND fn.nametype = '9' AND fn.language= '1';
END;

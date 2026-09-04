from datetime import datetime
import json
import os
import re
import networkx as nx
import pandas as pd
import spacy
from spacy.pipeline import EntityRuler

# 1. Initialize spaCy NLP pipeline
try:
  nlp = spacy.load("en_core_web_sm")
except OSError:
  nlp = spacy.blank("en")

# 2. Add domain-specific entity ruler patterns
if "entity_ruler" not in nlp.pipe_names:
  ruler = nlp.add_pipe(
      "entity_ruler", before="ner" if "ner" in nlp.pipe_names else None
  )
  patterns = [
      {
          "label": "CASE_NUMBER",
          "pattern": [{"TEXT": {"REGEX": r"^[A-Z]{2}\d{6}$"}}],
      },
      {
          "label": "PRIMARY_CRIME",
          "pattern": [
              {
                  "LOWER": {
                      "IN": [
                          "theft",
                          "battery",
                          "assault",
                          "robbery",
                          "armed robbery",
                          "narcotics",
                          "burglary",
                          "homicide",
                          "criminal damage",
                          "motor vehicle theft",
                      ]
                  }
              }
          ],
      },
      {
          "label": "PREMISE",
          "pattern": [
              {
                  "LOWER": {
                      "IN": [
                          "residence",
                          "sidewalk",
                          "street",
                          "gas station / convenience store",
                          "gas station",
                          "parking lot",
                          "apartment",
                          "alley",
                          "department store",
                          "restaurant",
                          "commercial building",
                          "bar or tavern",
                          "vehicle non-commercial",
                      ]
                  }
              }
          ],
      },
  ]
  ruler.add_patterns(patterns)


def parse_fir_with_spacy(fir_text: str) -> dict:
  """Extracts structured attributes from raw FIR narrative text."""
  doc = nlp(fir_text)

  # 1. Core Regex & Token Extraction
  case_num = re.search(r"\b([A-Z]{2}\d{6})\b", fir_text)
  date_time = re.search(
      r"(\d{2}/\d{2}/\d{4})\s+at\s+(?:approximately\s+)?(\d{2}:\d{2})",
      fir_text,
  )
  primary_crime = re.search(
      r"\b(ARMED"
      r" ROBBERY|ROBBERY|THEFT|BATTERY|BURGLARY|ASSAULT|NARCOTICS|HOMICIDE|MOTOR"
      r" VEHICLE THEFT|CRIMINAL DAMAGE)\b",
      fir_text,
      re.IGNORECASE,
  )
  crime_subtype = re.search(
      r"involving\s+([A-Z0-9\$\s:]+?)\s+was\s+reported", fir_text, re.IGNORECASE
  )
  block = re.search(
      r"reported at\s+([0-9]{4,5}X{1,2}\s+[NSEW]\s+[A-Z0-9\s]+?),\s+situated",
      fir_text,
  )
  district = re.search(r"District\s+(\d{3})", fir_text)
  beat = re.search(r"Beat\s+(\d{4})", fir_text)
  ward = re.search(r"Ward\s+(\d{1,2})", fir_text)
  comm_area = re.search(r"Community Area\s+(\d{1,2})", fir_text)
  premise = re.search(
      r"(?:on/at a|in an?|at a)\s+([A-Z0-9\s/]+?)\.\s+The\s+suspect",
      fir_text,
      re.IGNORECASE,
  )
  suspect = re.search(
      r"identified\s+as\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", fir_text
  )

  # 2. Vehicle Plate Extraction (returns None if absent)
  vehicle_plate = re.search(
      r"\b(?:license plate|vehicle|plate number|bearing license plate)\s+([A-Z]{2}[-\s]?\d{2,4}[-\s]?[A-Z0-9]{1,4})\b",
      fir_text,
      re.IGNORECASE,
  )

  iucr = re.search(
      r"IUCR\s*code\s*([0-9]{3,4}[A-Z]?)", fir_text, re.IGNORECASE
  )
  fbi_code = re.search(
      r"FBI\s*Code\s*([0-9]{1,2}[A-Z]?)", fir_text, re.IGNORECASE
  )

  # Suspect resolution fallback via spaCy PERSON entities
  suspect_name = suspect.group(1).strip() if suspect else None
  if not suspect_name:
    persons = [
        ent.text.strip()
        for ent in doc.ents
        if ent.label_ in ["PERSON", "PER"] and len(ent.text.strip()) > 2
    ]
    if persons:
      suspect_name = persons[0]

  # Binary flags
  arrest = bool(re.search(r"ARREST MADE", fir_text, re.IGNORECASE))
  domestic = bool(
      re.search(r"Domestic dispute:\s*YES", fir_text, re.IGNORECASE)
  )

  # Datetime formatting
  dt_formatted, year_val = None, None
  if date_time:
    d_p, t_p = date_time.group(1), date_time.group(2)
    try:
      parsed_dt = datetime.strptime(f"{d_p} {t_p}", "%m/%d/%Y %H:%M")
      dt_formatted = parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
      year_val = parsed_dt.year
    except ValueError:
      dt_formatted = f"{d_p} {t_p}"

  return {
      "case_number": case_num.group(1) if case_num else None,
      "suspect_name": suspect_name,
      "vehicle_plate": (
          vehicle_plate.group(1).strip() if vehicle_plate else None
      ),
      "date": dt_formatted,
      "year": year_val,
      "primary_type": (
          primary_crime.group(1).upper() if primary_crime else None
      ),
      "description": (
          crime_subtype.group(1).strip() if crime_subtype else None
      ),
      "block": block.group(1).strip() if block else None,
      "location_description": (
          premise.group(1).strip().upper() if premise else None
      ),
      "district": district.group(1) if district else None,
      "beat": beat.group(1) if beat else None,
      "ward": int(ward.group(1)) if ward else None,
      "community_area": int(comm_area.group(1)) if comm_area else None,
      "iucr": iucr.group(1) if iucr else None,
      "fbi_code": fbi_code.group(1) if fbi_code else None,
      "arrest": arrest,
      "domestic": domestic,
  }


def build_crime_graph_from_records(records: list) -> nx.Graph:
  """Builds a multi-entity NetworkX graph linking suspects, crime types, locations, vehicles, and beats."""
  G = nx.Graph()
  for r in records:
    c_num = r.get("case_number")
    if not c_num:
      continue

    # 1. Case node
    G.add_node(
        c_num,
        id=c_num,
        label=f"Case #{c_num}",
        type="CASE",
        date=str(r.get("date")),
        arrest=bool(r.get("arrest")),
        domestic=bool(r.get("domestic")),
    )

    # 2. Suspect node & edge
    if r.get("suspect_name"):
      suspect = r["suspect_name"]
      G.add_node(suspect, id=suspect, label=suspect, type="SUSPECT")
      G.add_edge(c_num, suspect, relationship="PERPETRATED_BY")

    # 3. Crime Type node & edge
    if r.get("primary_type"):
      crime = r["primary_type"]
      G.add_node(crime, id=crime, label=crime, type="CRIME_TYPE")
      G.add_edge(c_num, crime, relationship="OFFENSE_TYPE")

    # 4. Police Beat node & edge
    if r.get("beat"):
      beat_id = f"Beat {r['beat']}"
      G.add_node(
          beat_id,
          id=beat_id,
          label=beat_id,
          type="POLICE_BEAT",
          district=str(r.get("district")),
      )
      G.add_edge(c_num, beat_id, relationship="OCCURRED_IN_BEAT")

    # 5. Location node & edge
    if r.get("block"):
      loc = r["block"]
      G.add_node(
          loc,
          id=loc,
          label=loc,
          type="LOCATION",
          premise=str(r.get("location_description")),
      )
      G.add_edge(c_num, loc, relationship="OCCURRED_AT")

    # 6. Vehicle node & edges (ONLY created if vehicle_plate is present)
    if r.get("vehicle_plate"):
        plate = r["vehicle_plate"]
    G.add_node(plate, id=plate, label=plate, type="VEHICLE")

    if r.get("suspect_name"):
        G.add_edge(
            r["suspect_name"],
            plate,
            relationship="DRIVES_VEHICLE"
        )

  return G


def export_graph_to_json(
    G: nx.Graph, output_filename: str = "crime_kg_nodes_edges.json"
):
  """Converts the NetworkX graph to standard node-link JSON format and writes to disk."""
  graph_data = nx.node_link_data(G, edges="edges")

  formatted_json = {
      "nodes": [
          {"id": n["id"], **{k: v for k, v in n.items() if k != "id"}}
          for n in graph_data["nodes"]
      ],
      "edges": [
          {
              "source": e["source"],
              "target": e["target"],
              "relationship": e.get("relationship", "CONNECTED"),
          }
          for e in graph_data["edges"]
      ],
  }

  with open(output_filename, "w", encoding="utf-8") as f:
    json.dump(formatted_json, f, indent=2)

  print(
      f"Graph JSON exported: '{output_filename}'"
      f" ({len(formatted_json['nodes'])} Nodes, {len(formatted_json['edges'])}"
      " Edges)."
  )


if __name__ == "__main__":
  input_file = "fir_reports.txt"
  output_csv = "extracted_chicago_crimes.csv"
  output_json = "crime_kg_nodes_edges.json"

  if not os.path.exists(input_file):
    raise FileNotFoundError(
        f"'{input_file}' not found. Please place it in the same directory."
    )

  # 1. Read delimited FIR text file
  with open(input_file, "r", encoding="utf-8") as f:
    raw_reports = [r.strip() for r in f.read().split("---") if r.strip()]

  print(f"Loaded {len(raw_reports)} FIR reports from '{input_file}'.")

  # 2. Extract structured entities
  extracted_records = [parse_fir_with_spacy(report) for report in raw_reports]

  # 3. Save to CSV
  df = pd.DataFrame(extracted_records)
  df.to_csv(output_csv, index=False)
  print(f"Successfully saved {len(df)} records to '{output_csv}'.")

  # 4. Construct Graph
  crime_graph = build_crime_graph_from_records(extracted_records)
  print(
      f"Knowledge Graph: {crime_graph.number_of_nodes()} Nodes,"
      f" {crime_graph.number_of_edges()} Edges."
  )

  # 5. Export Graph Nodes and Edges to JSON
  export_graph_to_json(crime_graph, output_json)
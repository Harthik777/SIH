import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD
from urllib.parse import quote


# ============================================================
# FILES
# ============================================================

ONTOLOGY_FILE = "final_ontology.ttl"
CSV_FILE = "crime_dataset.csv"
OUTPUT_FILE = "populated_crime_ontology.ttl"


# ============================================================
# LOAD ONTOLOGY
# ============================================================

g = Graph()
g.parse(ONTOLOGY_FILE, format="turtle")

BASE = Namespace(
    "urn:webprotege:ontology:"
    "5ec59a45-72d3-47b0-ba41-ae665fe28b44#"
)


# ============================================================
# CLASSES
# ============================================================

CrimeIncident = URIRef(
    "http://webprotege.stanford.edu/RiGN18DuwG0dwq6FjCKSYo"
)

Suspect = URIRef(
    "http://webprotege.stanford.edu/R8qyDgnMRI1NDAPDbXqOJhA"
)

Vehicle = URIRef(
    "http://webprotege.stanford.edu/RBlXdpZVUuREsaAn9m9t6bD"
)

CrimeType = URIRef(
    "http://webprotege.stanford.edu/RhSSPaCkjO87glJlSpBOH1"
)

CrimeDescription = URIRef(
    "http://webprotege.stanford.edu/RCkeJzJjnHtjgJd63gPedgh"
)

Location = URIRef(
    "http://webprotege.stanford.edu/RBI9KWuczNzFDsnwLPgXFcJ"
)

PremiseType = URIRef(
    "http://webprotege.stanford.edu/RB2VG02jy0BqfL5TCLbqbfP"
)

PoliceDistrict = URIRef(
    "http://webprotege.stanford.edu/R8j3tBFApKvFaJioaM9ZKNo"
)

PoliceBeat = URIRef(
    "http://webprotege.stanford.edu/RCyS0jvr0ScQnZKBLPlm2NX"
)

Ward = URIRef(
    "http://webprotege.stanford.edu/RDBTCEfQVMuTIq3MlGex2Ct"
)

CommunityArea = URIRef(
    "http://webprotege.stanford.edu/R9TGhjCsJo6Fr6RM2vqiQKC"
)

IUCRCode = URIRef(
    "http://webprotege.stanford.edu/RDUjYdiNBbSPMctQIsCKCO5"
)

FBICode = URIRef(
    "http://webprotege.stanford.edu/RBtJy2UD9MNQZbkl9uLh4G0"
)


# ============================================================
# OBJECT PROPERTIES
# ============================================================

hasSuspect = URIRef(
    "http://webprotege.stanford.edu/RCPaYi7rJJZTvqhGhjWgGGL"
)

drivesVehicle = URIRef(
    "http://webprotege.stanford.edu/RDXMtjmH9XH5ITULlLOKolQ"
)

hasCrimeType = URIRef(
    "http://webprotege.stanford.edu/RCpWgKB2OZXwOZcfDxmAGn5"
)

hasDescription = URIRef(
    "http://webprotege.stanford.edu/RCaEofYrluUvidZ0qaAkVCi"
)

occurredAt = URIRef(
    "http://webprotege.stanford.edu/RDE0C8I90tefxRln4Dpr4NY"
)

hasPremiseType = URIRef(
    "http://webprotege.stanford.edu/RoB9KlzV0pvxKPjasHwlPQ"
)

occurredInDistrict = URIRef(
    "http://webprotege.stanford.edu/RcmXi1zXPEXrekCVsEvOYD"
)

occurredInBeat = URIRef(
    "http://webprotege.stanford.edu/RxU6Wg2CvLTDORvRlE682d"
)

occurredInWard = URIRef(
    "http://webprotege.stanford.edu/R8KkiVzmeIM3dAHZF3cCT6A"
)

occurredInCommunityArea = URIRef(
    "http://webprotege.stanford.edu/R6HaI2Gp3U8rkyo4sXVXQt"
)

hasIUCRCode = URIRef(
    "http://webprotege.stanford.edu/R8FohkqcO0XkCwTC95YMxBd"
)

hasFBICode = URIRef(
    "http://webprotege.stanford.edu/R7ijEjSV1ZavXlcmZ1wO8aD"
)


# ============================================================
# DATA PROPERTIES
# ============================================================

hasCaseNumber = URIRef(
    "http://webprotege.stanford.edu/RaFlYt4cVpUJhIUDoLBtWa"
)

hasDateTime = URIRef(
    "http://webprotege.stanford.edu/RCYN67wnnEtMz2PpW9tOnQj"
)

hasYear = URIRef(
    "http://webprotege.stanford.edu/R9asZ9vOi6HT1xyYkz63wsZ"
)

hasArrest = URIRef(
    "http://webprotege.stanford.edu/R17VScv8dd557RfPyfFOIl"
)

isDomesticDispute = URIRef(
    "http://webprotege.stanford.edu/R9Wzc0ZoQJ91EsUgxbbPysT"
)

hasLocationBlock = URIRef(
    "http://webprotege.stanford.edu/R8ZugcK1oJnApePFYZTwzTB"
)

hasVehiclePlate = URIRef(
    "http://webprotege.stanford.edu/RBETPIaD0grWLZBtZx3Tpwy"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def safe_uri(value):

    return quote(
        str(value).strip().replace(" ", "_"),
        safe="_-"
    )


# ============================================================
# LOAD CSV
# ============================================================

df = pd.read_csv(CSV_FILE)

print("Rows loaded:", len(df))


# ============================================================
# PROCESS EACH ROW
# ============================================================

for _, row in df.iterrows():

    # --------------------------------------------------------
    # VALUES
    # --------------------------------------------------------

    case_number = clean(row["case_number"])
    suspect_name = clean(row["suspect_name"])
    vehicle_plate = clean(row["vehicle_plate"])

    date_value = clean(row["date"])
    year_value = clean(row["year"])

    primary_type = clean(row["primary_type"])
    description = clean(row["description"])

    block = clean(row["block"])
    premise = clean(row["location_description"])

    district = clean(row["district"])
    beat = clean(row["beat"])
    ward = clean(row["ward"])
    community_area = clean(row["community_area"])

    iucr = clean(row["iucr"])
    fbi = clean(row["fbi_code"])

    arrest = clean(row["arrest"])
    domestic = clean(row["domestic"])


    # --------------------------------------------------------
    # CRIME INCIDENT
    # --------------------------------------------------------

    if not case_number:
        continue

    incident_uri = BASE[
        f"CrimeIncident_{safe_uri(case_number)}"
    ]

    g.add((
        incident_uri,
        RDF.type,
        CrimeIncident
    ))

    g.add((
        incident_uri,
        hasCaseNumber,
        Literal(
            case_number,
            datatype=XSD.string
        )
    ))


    # --------------------------------------------------------
    # SUSPECT
    # --------------------------------------------------------

    suspect_uri = None

    if suspect_name:

        suspect_uri = BASE[
            f"Suspect_{safe_uri(suspect_name)}"
        ]

        g.add((
            suspect_uri,
            RDF.type,
            Suspect
        ))

        g.add((
            incident_uri,
            hasSuspect,
            suspect_uri
        ))


    # --------------------------------------------------------
    # CRIME TYPE
    # --------------------------------------------------------

    if primary_type:

        crime_type_uri = BASE[
            f"CrimeType_{safe_uri(primary_type)}"
        ]

        g.add((
            crime_type_uri,
            RDF.type,
            CrimeType
        ))

        g.add((
            incident_uri,
            hasCrimeType,
            crime_type_uri
        ))


    # --------------------------------------------------------
    # CRIME DESCRIPTION
    # --------------------------------------------------------

    if description:

        description_uri = BASE[
            f"CrimeDescription_{safe_uri(description)}"
        ]

        g.add((
            description_uri,
            RDF.type,
            CrimeDescription
        ))

        g.add((
            incident_uri,
            hasDescription,
            description_uri
        ))


    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if block:

        location_uri = BASE[
            f"Location_{safe_uri(block)}"
        ]

        g.add((
            location_uri,
            RDF.type,
            Location
        ))

        g.add((
            incident_uri,
            occurredAt,
            location_uri
        ))

        g.add((
            location_uri,
            hasLocationBlock,
            Literal(
                block,
                datatype=XSD.string
            )
        ))


    # --------------------------------------------------------
    # PREMISE TYPE
    # --------------------------------------------------------

    if premise:

        premise_uri = BASE[
            f"PremiseType_{safe_uri(premise)}"
        ]

        g.add((
            premise_uri,
            RDF.type,
            PremiseType
        ))

        g.add((
            incident_uri,
            hasPremiseType,
            premise_uri
        ))


    # --------------------------------------------------------
    # POLICE DISTRICT
    # --------------------------------------------------------

    if district:

        district_uri = BASE[
            f"PoliceDistrict_{safe_uri(district)}"
        ]

        g.add((
            district_uri,
            RDF.type,
            PoliceDistrict
        ))

        g.add((
            incident_uri,
            occurredInDistrict,
            district_uri
        ))


    # --------------------------------------------------------
    # POLICE BEAT
    # --------------------------------------------------------

    if beat:

        beat_uri = BASE[
            f"PoliceBeat_{safe_uri(beat)}"
        ]

        g.add((
            beat_uri,
            RDF.type,
            PoliceBeat
        ))

        g.add((
            incident_uri,
            occurredInBeat,
            beat_uri
        ))


    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    if ward:

        ward_uri = BASE[
            f"Ward_{safe_uri(ward)}"
        ]

        g.add((
            ward_uri,
            RDF.type,
            Ward
        ))

        g.add((
            incident_uri,
            occurredInWard,
            ward_uri
        ))


    # --------------------------------------------------------
    # COMMUNITY AREA
    # --------------------------------------------------------

    if community_area:

        community_uri = BASE[
            f"CommunityArea_{safe_uri(community_area)}"
        ]

        g.add((
            community_uri,
            RDF.type,
            CommunityArea
        ))

        g.add((
            incident_uri,
            occurredInCommunityArea,
            community_uri
        ))


    # --------------------------------------------------------
    # IUCR CODE
    # --------------------------------------------------------

    if iucr:

        iucr_uri = BASE[
            f"IUCRCode_{safe_uri(iucr)}"
        ]

        g.add((
            iucr_uri,
            RDF.type,
            IUCRCode
        ))

        g.add((
            incident_uri,
            hasIUCRCode,
            iucr_uri
        ))


    # --------------------------------------------------------
    # FBI CODE
    # --------------------------------------------------------

    if fbi:

        fbi_uri = BASE[
            f"FBICode_{safe_uri(fbi)}"
        ]

        g.add((
            fbi_uri,
            RDF.type,
            FBICode
        ))

        g.add((
            incident_uri,
            hasFBICode,
            fbi_uri
        ))


    # ========================================================
    # SUSPECT'S VEHICLE
    # ========================================================
    #
    # vehicle_plate is the plate extracted from the FIR
    # for the vehicle associated with the suspect.
    #
    # It is NOT the stolen/affected vehicle.
    #
    # Relationship:
    #
    # Suspect
    #    |
    #    | drivesVehicle
    #    ↓
    # Vehicle
    #    |
    #    | hasVehiclePlate
    #    ↓
    # License Plate
    #
    # If vehicle_plate is NULL:
    # NO Vehicle node is created.
    # ========================================================

    if vehicle_plate and suspect_uri:

        vehicle_uri = BASE[
            f"Vehicle_{safe_uri(vehicle_plate)}"
        ]

        # Vehicle node
        g.add((
            vehicle_uri,
            RDF.type,
            Vehicle
        ))

        # Suspect -> Vehicle
        g.add((
            suspect_uri,
            drivesVehicle,
            vehicle_uri
        ))

        # Vehicle -> License Plate
        g.add((
            vehicle_uri,
            hasVehiclePlate,
            Literal(
                vehicle_plate,
                datatype=XSD.string
            )
        ))


    # --------------------------------------------------------
    # DATE / TIME
    # --------------------------------------------------------

    if date_value:

        try:

            datetime_value = pd.to_datetime(
                date_value
            )

            g.add((
                incident_uri,
                hasDateTime,
                Literal(
                    datetime_value.isoformat(),
                    datatype=XSD.dateTime
                )
            ))

        except Exception:

            pass


    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    if year_value:

        try:

            year_int = int(float(year_value))

            g.add((
                incident_uri,
                hasYear,
                Literal(
                    year_int,
                    datatype=XSD.integer
                )
            ))

        except Exception:

            pass


    # --------------------------------------------------------
    # ARREST
    # --------------------------------------------------------

    if arrest:

        arrest_lower = arrest.lower()

        if arrest_lower in ["true", "1", "yes"]:

            arrest_bool = True

        elif arrest_lower in ["false", "0", "no"]:

            arrest_bool = False

        else:

            arrest_bool = None

        if arrest_bool is not None:

            g.add((
                incident_uri,
                hasArrest,
                Literal(
                    arrest_bool,
                    datatype=XSD.boolean
                )
            ))


    # --------------------------------------------------------
    # DOMESTIC DISPUTE
    # --------------------------------------------------------

    if domestic:

        domestic_lower = domestic.lower()

        if domestic_lower in ["true", "1", "yes"]:

            domestic_bool = True

        elif domestic_lower in ["false", "0", "no"]:

            domestic_bool = False

        else:

            domestic_bool = None

        if domestic_bool is not None:

            g.add((
                incident_uri,
                isDomesticDispute,
                Literal(
                    domestic_bool,
                    datatype=XSD.boolean
                )
            ))


# ============================================================
# SAVE POPULATED ONTOLOGY
# ============================================================

g.serialize(
    destination=OUTPUT_FILE,
    format="turtle"
)


# ============================================================
# DONE
# ============================================================

print()
print("======================================")
print("POPULATION COMPLETE")
print("======================================")
print("Rows processed:", len(df))
print("Total triples:", len(g))
print("Output file:", OUTPUT_FILE)
print("======================================")
#!/usr/bin/env python3
"""VALODY: Assign vaginal time-series into dynamic categories based on VALENCIA
output results.
"""
__author__ = "Luisa W. Hugerth"
__date__ = "2023-04"
__version__ = "0.1"

from pathlib import Path
import argparse
import sys
import warnings

try:
    import pandas as pd
except ImportError as e:
    print("Required package pandas not available:", e)
    exit(1)

warnings.filterwarnings("ignore")

ALL_CSTs = {
    "I",
    "II",
    "III",
    "IV-A",
    "IV-B",
    "IV-C",
    "V",
}
ALL_SUBTYPE_CSTs = {
    "I-A",
    "I-B",
    "II-A",
    "II-B",
    "III-A",
    "III-B",
    "IV-A",
    "IV-B",
    "IV-C0",
    "IV-C1",
    "IV-C2",
    "IV-C3",
    "IV-C4",
    "V",
}

def parse_args():
    parser = argparse.ArgumentParser(
        description=f"{__doc__} Copyright (c) {__author__}, {__date__}",
        epilog=f"Version v{__version__}",
    )

    parser.add_argument("-i", "--input", required=True ,
        help="Path to VALENCIA output.")
    parser.add_argument( "-m", "--metadata",
        help="CSV file with 'sampleID,subjectID,menses', where menses takes 1 for yes and 0 for no")
    parser.add_argument( "-o", "--output", 
        default="valody.out.csv",
        help="Output filename [%(default)s].")
    parser.add_argument("-s", "--subtypes", action="store_true",
        default=False,
        help="Use CST subtypes instead of main types; requires eubiosis and dysbiosis argument")
    parser.add_argument("-d", "--dysbiosis",
        default="III,IV-A,IV-B,IV-C",
        help="Comma-separated list of CST or sub-CST considered dysbiotic [%(default)s].")
    parser.add_argument("-e", "--eubiosis",
        default="I,II,V",
        help="Comma-separated list of CST or sub-CST considered eubiotic [%(default)s].")

    if len(sys.argv) < 2:
        parser.print_help()
        exit(1)
    
    args = parser.parse_args()

    return args


def assign_dynamics(valencia, metadata, subjID, eubiotic, dysbiotic, subtypes):
    """Assign dynamics classification for one individual
    """
    all_ids = set(metadata.set_index(["subjectID"]).loc[(subjID)]["sampleID"])
    samples_per_subject = valencia[valencia["sampleID"].isin(all_ids)]
    if subtypes:
        counts_subject = samples_per_subject.groupby("subCST")[["sampleID"]].count()
    else:
        counts_subject = samples_per_subject.groupby("CST")[["sampleID"]].count()

    eubio = counts_subject[counts_subject.index.isin(eubiotic)].sum()
    dysbio = counts_subject[counts_subject.index.isin(dysbiotic)].sum()
    eu_rate = float(eubio / (eubio + dysbio))
    dys_rate = float(dysbio / (eubio + dysbio))

    if eu_rate >= 0.8:
        return "Constant eubiotic"
    elif dys_rate >= 0.8:
        return "Constant dysbiotic"
    else:
        midcycle = set(
            metadata.set_index(["subjectID", "menses"]).loc[(subjID, 0)]["sampleID"]
        )
        samples_per_subject = valencia[valencia["sampleID"].isin(midcycle)]

        if subtypes:
            counts_subject = samples_per_subject.groupby("subCST")[["sampleID"]].count()
        else:
            counts_subject = samples_per_subject.groupby("CST")[["sampleID"]].count()

        eubio = counts_subject[counts_subject.index.isin(eubiotic)].sum()
        dysbio = counts_subject[counts_subject.index.isin(dysbiotic)].sum()
        eu_rate = float(eubio / (eubio + dysbio))

        if eu_rate >= 0.8:
            return "Menses dysbiotic"
        else:
            return "Unstable"


def validate_csts(eubiosis, dysbiosis, subtypes=False):
    """Validate that all CST are present in either eubiosis and dysbiosis classes.
    """
    eu_cst = set(eubiosis.split(sep=","))
    dys_cst = set(dysbiosis.split(sep=","))
    all_cst = eu_cst.union(dys_cst)

    cst_both_eu_and_dys = eu_cst.intersection(dys_cst)
    if cst_both_eu_and_dys:
        print(f"A CST cannot be eubiotic and dysbiotic at once: {cst_both_eu_and_dys}")
        sys.exit(1)

    if subtypes:
        if all_cst != ALL_SUBTYPE_CSTs:
            print(f"ERROR: When using subtypes, the following CSTs must be included: {ALL_SUBTYPE_CSTs}")
            sys.exit(1)
    else:
        if all_cst != ALL_CSTs:
            print(f"ERROR: The following CST must be included: {ALL_CSTs}")
            sys.exit(1)

    return eu_cst, dys_cst


def check_sampleid_overlaps(metadata, valencia):
    """Check that sample IDs exist in both metadata and VALENCIA data.

    If there are samples without either metadata or VALENCIA data, print
    warnings and proceed.
    """
    all_meta_ids = set(metadata["sampleID"])
    all_val_ids = set(valencia["sampleID"])
    only_meta = all_meta_ids.difference(all_val_ids)
    only_val = all_val_ids.difference(all_meta_ids)
    if len(only_meta) > 0:
        print(f"WARNING: {len(only_meta)} sampleIDs in metadata not found in the Valencia table!")
    if len(only_val) > 0:
        print(f"WARNING: {len(only_val)} sampleIDs in VALENCIA output not found in the metadata!")


def main(input, metadata, eubiosis, dysbiosis, subtypes):
    # Step 1: read the Valencia output and store type for each sample
    try:
        valencia = pd.read_csv(input, sep=",")
    except Exception as e:
        print(e)
        print(f"ERROR: Please provide a valid path to the VALENCIA output using -i")
        exit(1)

    # Step 2: read the metadata file
    try:
        metadata = pd.read_csv(metadata, sep=",")
    except Exception as e:
        print(e)
        print(f"ERROR: Please provide a valid path to the metadata using -m")
        exit(1)

    eu_cst, dys_cst = validate_csts(eubiosis, dysbiosis, subtypes)
    check_sampleid_overlaps(metadata, valencia)

    allsubjects = metadata["subjectID"].unique()
    dynamics = list()
    for i in range(len(allsubjects)):
        subj = allsubjects[i]
        dynamic = assign_dynamics(valencia, metadata, subj, eu_cst, dys_cst, subtypes)
        dynamics.append(dynamic)

    valody_classifications = pd.DataFrame(dynamics, allsubjects, columns=["Dynamics"])
    valody_classifications.to_csv(args.output, index_label="SampleID", sep=",")


if __name__ == "__main__":
    args = parse_args()

    if Path(args.output).exists() and Path(args.output).is_file():
        print(f"WARNING: Overwriting output file: {args.output}")

    main(
        args.input,
        args.metadata,
        args.eubiosis,
        args.dysbiosis,
        args.subtypes,
    )
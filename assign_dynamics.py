#!/usr/bin/env python3
"""VALODY: Assign vaginal time-series into dynamic categories based on VALENCIA
output results.
"""
__author__ = "Luisa W. Hugerth"
__date__ = "2023-04"
__version__ = "0.1"

from collections import Counter
import argparse
import sys
import warnings

try:
    import pandas as pd
except ImportError as e:
    print("Required package pandas not available:", e)
    exit(1)

warnings.filterwarnings("ignore")


def parse_args():
    parser = argparse.ArgumentParser(
        description=f"{__doc__} Copyright (c) {__author__}, {__date__}",
        epilog=f"Version v{__version__}",
    )

    parser.add_argument("-i", "--input", 
        help="Path to VALENCIA output", required=True)
    parser.add_argument( "-m", "--metadata",
        help="CSV file with 'sampleID,subjectID,menses', where menses takes 1 for yes and 0 for no")
    parser.add_argument( "-o", "--output", 
        default="valody.out.csv",
        help="Output csv file prefix")
    parser.add_argument("-s", "--subtypes", action="store_true",
        default=False,
        help="Use CST subtypes instead of main types; requires eubiosis and dysbiosis argument")
    parser.add_argument("-d", "--dysbiosis",
        default="III,IV-A,IV-B,IV-C",
        help="comma-separated list of CST or sub-CST considered dysbiotic")
    parser.add_argument("-e", "--eubiosis",
        default="I,II,V",
        help="comma-separated list of CST or sub-CST considered eubiotic",
    )

    if len(sys.argv) < 2:
        parser.print_help()
        exit(1)
    
    args = parser.parse_args()

## This function assigns for one individual at a time

    return args

def assign_dynamics(valencia, metadata, subjID, eubiotic, dysbiotic, subtypes):
    allids = set(metadata.set_index(["subjectID"]).loc[(subjID)]["sampleID"])
    samples_per_subject = valencia[valencia["sampleID"].isin(allids)]
    if subtypes:
        counts_subject = samples_per_subject.groupby("subCST")[["sampleID"]].count()
    else:
        counts_subject = samples_per_subject.groupby("CST")[["sampleID"]].count()

    eubio = counts_subject[counts_subject.index.isin(eubiotic)].sum()
    dysbio = counts_subject[counts_subject.index.isin(dysbiotic)].sum()
    eu_rat = float(eubio / (eubio + dysbio))
    dys_rat = float(dysbio / (eubio + dysbio))

    if eu_rat >= 0.8:
        return "Constant eubiotic"
    elif dys_rat >= 0.8:
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
        eu_rat = float(eubio / (eubio + dysbio))

        if eu_rat >= 0.8:
            return "Menses dysbiotic"
        else:
            return "Unstable"


# test if all CST are accounted for; only implemented for main CST
if args.subtypes:
    eu_cst = args.eubiosis.split(sep=",")
    dys_cst = args.dysbiosis.split(sep=",")
    all_cst = eu_cst + dys_cst
    if set(all_cst) != {
        "I-A",
        "I-B",
        "II-A",
        "II-B",
        "III-A",
        "III-B",
        "V",
        "IV-A",
        "IV-B",
        "IV-C0",
        "IV-C1",
        "IV-C2",
        "IV-C3",
        "IV-C4",
    }:
        sys.exit(
            'When using subtypes, the  following CST must be included: \
                "I-A", "I-B", "II-A", "II-B", "III-A", "III-B",\
                "IV-A", "IV-B", "IV-C0", "IV-C1", "IV-C2", "IV-C3", "IV-C4", "V"'
        )
    if len(set(eu_cst).intersection(dys_cst)) > 0:
        sys.exit("A CST cannot be eubiotic and dysbiotic at once")

else:
    eu_cst = args.eubiosis.split(sep=",")
    dys_cst = args.dysbiosis.split(sep=",")
    all_cst = eu_cst + dys_cst
    if set(all_cst) != {"I", "II", "III", "IV-A", "IV-B", "IV-C", "V"}:
        sys.exit(
            'The following CST must be included: "I", "II", "III", "IV-A", "IV-B", "IV-C", "V"'
        )
    if len(set(eu_cst).intersection(dys_cst)) > 0:
        sys.exit("A CST cannot be eubiotic and dysbiotic at once")

# test if there are samples without metadata or without Valencia
# if so, warn and proceed
all_meta_ids = set(metadata["sampleID"])
all_val_ids = set(valencia["sampleID"])
only_meta = all_meta_ids.difference(all_val_ids)
only_val = all_val_ids.difference(all_meta_ids)
if len(only_meta) > 0:
    print(
        " ".join(
            [
                "Warning:",
                str(len(only_meta)),
                "sampleIDs in metadata not found in the Valencia table",
            ]
        )
    )
if len(only_val) > 0:
    print(
        " ".join(
            [
                "Warning:",
                str(len(only_val)),
                "sampleIDs in Valencia output not found in the metadata",
            ]
        )
    )


allsubjects = metadata["subjectID"].unique()
dynamics = list()
for i in range(len(allsubjects)):
    subj = allsubjects[i]
    dynamic = assign_dynamics(valencia, metadata, subj, eu_cst, dys_cst, args.subtypes)
    dynamics.append(dynamic)

to_print = pd.DataFrame(dynamics, allsubjects, columns=["Dynamics"])
to_print.to_csv(args.output, sep=",")

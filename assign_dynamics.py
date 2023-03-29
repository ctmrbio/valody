#!/usr/bin/env python3
""" Assigns vaginal dynamic categories
based on VALENCIA output results """
__author__ = "Luisa W. Hugerth"
__date__ = "2023"
__version__ = "0.1"

#import libraries
try:
    import pandas as pd
except:
    print("Required package pandas not available")
    #exit()

try:
    import argparse
except:
    print("Required package argparse not available")
    #exit()

try:
    from collections import Counter
except:
    print("Required package collections not available")

import warnings
warnings.filterwarnings('ignore')


#setting up expected arguments and help messages
parser = argparse.ArgumentParser(description="SNAPPYNAME is a tool to classify vaginal time-series into dynamic categories")

parser.add_argument("-i", "--input", help="Path to VALENCIA output",required=True)
parser.add_argument("-m", "--metadata", help="CSV file with 'sampleID,subjectID,menses', where menses takes 1 for yes and 0 for no")
parser.add_argument("-o","--output", help="Output csv file prefix", default="SNAPPYNAME.out.csv")
parser.add_argument("-s", "--subtypes", help="Use CST subtypes instead of main types; requires eubiosis and/or dysbiosis argument", 
                    action='store_true')
parser.add_argument("-d", "--dysbosis", help="comma-separated list of CST or sub-CST considered dysbiotic", default="III,IV")
parser.add_argument("-e", "--eubiosis", help="comma-separated list of CST or sub-CST considered eubiotic", default="I,II,V")     
args = parser.parse_args()


## Additional things to check:
# Are all CST included in either eubiosis or dysbiosis?
# If subtype, is eu/dys defined?
# Are all samples in the metadata also in the VALENCIA data?

## Need to implement all optional parameters
# Step 1: read the Valencia output and store type for each sample
try:
    valencia = pd.read_csv(args.input,sep=',') #change to args.input when wrapping
except:
    print('Please provide a valid path to the VALENCIA output using -i')
    exit()
    
# Step 2: read the metadata file
try:
    metadata = pd.read_csv(args.metadata,sep=',') #change to args.metadata when wrapping
except:
    print('Please provide a valid path to the metadata using -m')
    exit()
    
    
## This function assigns for one individual at a time

def assign_dynamics(valencia, metadata, subjID):
    allids = set(metadata.set_index(["subjectID"]).loc[(subjID)]["sampleID"])
    samples_per_subject = valencia[valencia["sampleID"].isin(allids)]
    counts_subject = samples_per_subject.groupby("CST")[["sampleID"]].count()
  
    eubio = counts_subject[counts_subject.index.isin(["I", "II", "V"])].sum()
    dysbio = counts_subject[counts_subject.index.isin(["III", "IV-A", "IV-B", "IV-C", "IV-D"])].sum()
    eu_rat = float(eubio / (eubio+dysbio))
    dys_rat = float(dysbio / (eubio+dysbio))

    if eu_rat >= 0.8:
        return("Constant eubiotic")
    elif dys_rat >= 0.8:
        return("Constant dysbiotic")
    else:
        midcycle = set(metadata.set_index(["subjectID", "menses"]).loc[(subjID,0)]["sampleID"])
        samples_per_subject = valencia[valencia["sampleID"].isin(midcycle)]
        counts_subject = samples_per_subject.groupby("CST")[["sampleID"]].count()
        counts_subject

        eubio = counts_subject[counts_subject.index.isin(["I", "II", "V"])].sum()
        dysbio = counts_subject[counts_subject.index.isin(["III", "IV-A", "IV-B", "IV-C", "IV-D"])].sum()
        eu_rat = float(eubio / (eubio+dysbio))

        if eu_rat >= 0.8:
            return("Menses dysbiotic")
        else:
            return("Unstable")    
            

allsubjects = metadata["subjectID"].unique()
dynamics = list()
for i in range(len(allsubjects)):
    subj = allsubjects[i]
    dynamic = assign_dynamics(valencia, metadata, subj)
    dynamics.append(dynamic)
        
to_print = pd.DataFrame(dynamics, allsubjects, columns = ["Dynamics"])
to_print.to_csv(args.output, sep=",")    
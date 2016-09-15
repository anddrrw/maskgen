import argparse

import scenario_model
import bulk_export
import graph_rules
import csv
import os

def validate_all(d, projects):
    with open(os.path.join(d, 'ErrorReport.csv'), 'wb') as csvfile:
        errorWriter = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for project in projects:
            name = os.path.basename(project)
            sm = scenario_model.ImageProjectModel(project)
            errorList = sm.validate()
            for err in errorList:
                errorWriter.writerow((name, str(err)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projectDir', help='Directory of projects')
    args = parser.parse_args()

    graph_rules.setup()

    projectList = bulk_export.pick_dirs(args.projectDir)

    validate_all(args.projectDir, projectList)

if __name__ == '__main__':
    main()
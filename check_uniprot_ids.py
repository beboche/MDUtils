import sys
import psycopg2
import psycopg2.extras
import urllib3
import certifi
import json
from insert_genes import get_db
import psycopg2.extras
# requires MobiDetails config module + database.ini file
from MobiDetailsApp import config


# check UNIPROT IDs

def log(level, text):
    print()
    if level == 'ERROR':
        sys.exit('[{0}]: {1}'.format(level, text))
    print('[{0}]: {1}'.format(level, text))


def main():
    # get db connector and cursor
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    i = 0

    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    curs.execute(
        "SELECT name, np, uniprot_id FROM gene ORDER BY name"
    )
    res = curs.fetchall()
    count = curs.rowcount
    i = 0
    for gene in res:
        # ncbi
        print('.', end="", flush=True)
        i += 1
        if i % 500 == 0:
            log('INFO', '{0}/{1} genes checked'.format(i, count))
        uniprot_url = 'https://www.ebi.ac.uk/proteins/api/proteins/refseq:{}?offset=0&size=100&reviewed=true'.format(gene['np'])
        uniprot_response = json.loads(http.request('GET', uniprot_url, headers={'Accept': 'application/json'}).data.decode('utf-8'))
        # print(uniprot_response[0]['accession'])
        try:
            if uniprot_response[0]['accession']:
                if gene['uniprot_id'] == uniprot_response[0]['accession']:
                    # print('INFO: RefSeq: {0} - {1} - {2} OK'.format(gene['np'], gene['name'][1], gene['name'][0]))
                    continue
                else:
                    curs.execute(
                        "UPDATE gene SET uniprot_id = '{0}' WHERE name[2] = '{1}'".format(uniprot_response[0]['accession'], gene['name'][1])
                    )
                    # print("UPDATE gene SET uniprot_id = '{0}' WHERE name[2] = '{1}'".format(uniprot_response[0]['accession'], gene['name'][1]))
                    log('WARNING', 'Updated gene UNIPROT ID of {0} - {1} from {2} to {3}'.format(
                        gene['name'][0],
                        gene['name'][1],
                        gene['uniprot_id'],
                        uniprot_response[0]['accession']
                    ))
                    i += 1
            else:
                log('WARNING', 'md_uniprot_id: {0} - RefSeq: {1} - {2} - {3} :not checked'.format(
                        gene['uniprot_id'],
                        gene['np'],
                        gene['name'][1],
                        gene['name'][0]
                    ))
        except Exception:
            log('WARNING', 'no UNIPROT ID {0} for {1} - {2}'.format(uniprot_response, gene['name'][1], gene['name'][0]))
    log('INFO', '{} isoforms updated'.format(i))

    db.commit()


if __name__ == '__main__':
    main()

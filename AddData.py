#!/usr/local/bin/python

"""
A number of functions to add data to Selaginella database from csv files or from sequence
files"""


import sys, getopt, csv, warnings, re
import MySQLdb as mdb
from Bio import SeqIO
from os import path


def main(argv):
  usage = 'AddData -f <function> -i <inputfile> -s <sequencefile> -d database_name'
  function = ''
  infilename = ''
  seqfilename = ''
  database = 'SelaginellaGenomics'
  name = ''
  try:
     opts, args = getopt.getopt(argv,"hf:i:s:d:n:",["function", "infile=", "seqfile=", "database=", "name="])
  except getopt.GetoptError:
     print usage
     sys.exit(2)
  for opt, arg in opts:
     if opt == '-h':
        print usage
        sys.exit()
     elif opt in ("-f", "--function"):
        function = arg
     elif opt in ("-i", "--infile"):
        infilename = arg
     elif opt in ("-s", "--seqfile"):
        seqfilename = arg
     elif opt in ("-d", "--database"):
        database = arg
     elif opt in ("-n", "--name"):
        name = arg
        
  if function == 'ref_coding':
    infilename = 1  #don't need a infile for this function. This prevents an error in the following lines
  if (not infilename and not seqfilename) or not function:
     sys.exit(usage)
  con = mdb.connect('localhost', 'root', '', database);
  with con:
    cur = con.cursor()
    if function == 'TAIR':
      add_TAIR(cur, infilename)
    if function == 'sequences':
      add_seqs(cur, infilename)
    if function == 'orthologs':
    #  add_ortholog_info(cur, infilename) 
      add_orthologs(cur, infilename)
    if function == 'coding':
      add_coding(cur, infilename)
    if function == 'ref_coding':
      ref_coding(cur)
    if function == 'nr':
      non_redundant(cur, infilename)
    if function == 'genbank':
      genbank(cur, infilename, seqfilename)
    if function == 'aligned':
      add_aligned(cur, seqfilename)
    if function == 'counts':
      add_counts(cur, infilename, name)

def add_counts(cur, infilename, name):
  infile = open(infilename, 'r')
  for line in infile.readlines():
    line = line.strip()
    (geneID, count) = line.split('\t')
    if geneID not in ('no_feature', 'ambiguous', 'too_low_aQual', 'not_aligned', 'alignment_not_unique'):
      cur.execute("SELECT * FROM Counts WHERE geneID = %s", (geneID))
      results = cur.fetchall()
      if len(results) == 1:
        #print "UPDATE Counts SET %s = '%s' WHERE geneID = '%s'" % (name, count, geneID)
        cur.execute("UPDATE counts SET %s = '%s' WHERE geneID = '%s'" % (name, count, geneID))
      elif len(results) == 0:
        #print "INSERT INTO Counts(geneID, %s) VALUES('%s', '%s')" % (name, geneID, count)
        cur.execute("INSERT INTO Counts(geneID, %s) VALUES('%s', '%s')" % (name, geneID, count))
      else:
        sys.exit("%s entries in DB for %s" % (len(results), geneID))
        
def add_aligned(cur, seqfilename):
  for sequence in SeqIO.parse(seqfilename, "fasta"):
    try:
      #print 'INSERT INTO Sequences(seqID, locus, accessionID, sequence)  VALUES(%s, %s, %s, %s)' , (seqID, locus, accessionID, sequence)
      cur.execute('UPDATE Sequences SET aligned = %s WHERE seqID = %s' , (sequence.seq.upper(), sequence.id))
    except mdb.IntegrityError, e:
      #warnings.warn("%s" % e)
      pass


"""add genbank sequences obtained using something like:
"blastdbcmd -db nt -entry_batch genbankIDs.txt >sequences.fa"

infile should have columns as follows:

seqID, locus, accessionID
"""
def genbank(cur, infilename, seqfilename):
  seqdict = SeqIO.to_dict(SeqIO.parse(seqfilename, "fasta"), key_function=get_accession)
  with open(infilename, 'rU') as f:
    reader=csv.reader(f,delimiter='\t')
    next(reader, None) 
    for row in reader:
      try:
        (accessionID, locus, seqID) = row
      except ValueError:
        warnings.warn("row length %s does not match the expected number of columns (3). Double-check delimiter" % len(row))
        continue
      sequence = seqdict[seqID].seq
      
      try:
        #print 'INSERT INTO Sequences(seqID, locus, accessionID, sequence)  VALUES(%s, %s, %s, %s)' , (seqID, locus, accessionID, sequence)
        cur.execute('INSERT INTO Sequences(seqID, locus, accessionID, sequence)  VALUES(%s, %s, %s, %s)' , (seqID, locus, accessionID, sequence))
      except mdb.IntegrityError, e:
        #warnings.warn("%s" % e)
        pass

def non_redundant(cur, infilename):
  for seq_record in SeqIO.parse(infilename, "fasta"):
    id = seq_record.id
    id = id.replace('|', '_')
    try:
      #print 'INSERT INTO Sequences(seqID, sequence, species, length)  VALUES(%s, %s, %s, %s)' % (id,seq,species,length)
      cur.execute('UPDATE OrthoGroups SET non_redundant = 1 WHERE geneID =  %s' , (id))
    except mdb.IntegrityError, e:
      #warnings.warn("%s" % e)
      pass


def add_orthologs(cur, infilename):
  infile = open(infilename, 'r')
  regex = re.compile('\d+')
  for line in infile.readlines():
    genes = line.split()
    group = genes.pop(0)
    group = regex.findall(group)[-1]
    for gene in genes:
      gene = gene.replace('|','_')
      gene = gene.replace('KRUS', 'KRAUS')
      try:
        #print "INSERT INTO OrthoGroups (geneID, orthoID) VALUES ('%s', '%s')" % (gene, group)
        cur.execute("INSERT INTO OrthoGroups (geneID, orthoID) VALUES (%s, %s)" , (gene, group))
      except mdb.IntegrityError, e:
        warnings.warn("%s" % e)
        sys.exit()
          
def add_TAIR(cur, infilename):
  infile = open(infilename, 'r')
  for line in infile.readlines():
    line = line.strip()
    fields = line.split('\t')
    locus = fields[0]
    if locus == 'Locus Identifier': #header row
      continue
    subfields = fields[2].split(';')
    description = subfields[0]
    try:
      symbol = fields[4]
    except IndexError:
      symbol = ''
    print "INSERT INTO tair (locus, description, symbol) VALUES ('%s', '%s', '%s')" % (locus, description, symbol)
    try:
      cur.execute("INSERT INTO tair (locus, description, symbol) VALUES (%s, %s, %s)", (locus, description, symbol))
    except mdb.IntegrityError, e:
      continue

def add_seqs(cur, infilename):
  for seq_record in SeqIO.parse(infilename, "fasta"):
    seq = seq_record.seq
    length = len(seq)
    #id = seq_record.id
    if 'comp' in seq_record.id:
      species = seq_record.id.split("comp")[0]
      #print species
      id = seq_record.id
    elif 'scaffold-' in seq_record.id:
      id = "_".join(seq_record.id.split("-")[1:3])
      species = seq_record.id.split("-")[1]
    elif 'EFJ' in seq_record.id:
      species = 'EFJ'
      id = seq_record.id.split(' ')[0].replace('EFJ', 'EFJ_')
    elif 'ADH' in seq_record.id:
      species = 'EFJ'
      id = 'EFJ_' + seq_record.id.split(' ')[0]
    try:
      #print 'INSERT INTO Sequences(seqID, sequence, species, length)  VALUES(%s, %s, %s, %s)' % (id,seq,species,length)
      cur.execute('INSERT INTO Sequences(seqID, sequence, species, length)  VALUES(%s, %s, %s, %s)' , (id,seq,species,length))
    except mdb.IntegrityError, e:
      #warnings.warn("%s" % e)
      pass

def add_coding(cur, infilename):
  """This will loop through a bed file of coding coordinates from transdecoder and add 
  info to the database. It is pretty straightforward EXCEPT that there's a bunch of info
  encoded in the name field that needs to be extracted"""
  with open(infilename, 'rU') as f:
    reader=csv.reader(f,delimiter='\t')
    for row in reader:
      try:
        (seqID, start, end, name, score, strand, thickStart, thickEnd, itemRgb, blockCount, blockSizes, blockStarts) = row
      except ValueError:
        continue
      species = name[3:name.find('comp')]
      geneID = species + '_' + name.split('|')[-1].split(':')[0].split('_')[0].replace('m.','')
      thickStart = int(thickStart) + 1
      if 'internal_len' in name.split('|')[-1].split(':')[1]:
        start_codon = 0
        stop_codon = 0
      elif '5prime_partial_len' in name.split('|')[-1].split(':')[1]:
        start_codon = 0
        stop_codon = 1
      elif '3prime_partial_len' in name.split('|')[-1].split(':')[1]:
        start_codon = 1
        stop_codon = 0
      elif 'complete_len' in name.split('|')[-1].split(':')[1]:
        start_codon = 1
        stop_codon = 1
      else:
        warnings.warn("could not parse %s" % name.split('|')[-1].split(':')[1])
      try:  
        #print 'INSERT INTO CodingSequences(geneID, seqID, species, start, end, strand, start_codon, stop_codon)  VALUES(%s, %s, %s, %s, %s, %s, %s, %s)' % (geneID, seqID, species, thickStart, thickEnd, strand, start_codon, stop_codon)
        cur.execute('INSERT INTO CodingSequences(geneID, seqID, species, start, end, strand, start_codon, stop_codon)  VALUES(%s, %s, %s, %s, %s, %s, %s, %s)', (geneID, seqID, species, thickStart, thickEnd, strand, start_codon, stop_codon))
      except mdb.IntegrityError, e:
        warnings.warn("%s" % e)
        pass
        
def ref_coding(cur):
  """This will loop through all non-BLUELEAF sequences (which are all CDSs) and add their
  info to the CodingSequences table (the info is the same as the Sequences table, but 
  keeping everything consistent will make life easier downstream):
  CodingSequences.geneID = Sequences.seqID
  CodingSequences.seqID = Sequences.seqID
  CodingSequences.start = 1
  CodingSequences.end = Sequences.length
  CodingSequences.strand = +
  CodingSequences.start_codon = NULL
  CodingSequences.stop_codon = NULL"""
  cur.execute("SELECT Sequences.seqid, Sequences.length, Sequences.species FROM Sequences, Species WHERE Sequences.species = Species.speciesID AND Species.source NOT LIKE 'BLUELEAF'")
  for (seqid, len, species) in cur.fetchall():
    try:
      cur.execute('INSERT INTO CodingSequences(geneID, seqID, species, start, end, strand)  VALUES(%s, %s, %s, %s, %s, %s)', (seqid, seqid, species, 1, len, '+'))
    except mdb.IntegrityError, e:
      warnings.warn("%s" % e)
      pass

"""This is an older function that I'm replacing with the orthomcl version"""        
def add_ortholog_info(cur, infilename):
  infile = open(infilename, 'r')
  for line in infile.readlines():
    line = line.strip()
    EFJ = line.split('\t')[1]
    if EFJ == 'Ensembl Transcript ID': #header row
      continue
    try:
      ATH = line.split('\t')[4]
    except IndexError:
      continue
    cur.execute("SELECT clusternum FROM sequences WHERE seqid = %s", (EFJ))
    try:
      clusternum = cur.fetchone()[0]
    except:
      continue
    cur.execute("UPDATE sequences SET clusternum = %s WHERE seqid = %s", (clusternum, ATH))
    print "UPDATE sequences SET clusternum = %s WHERE seqid = '%s'" % (clusternum, ATH)

def get_accession(record):
    """"Given a SeqRecord, return the accession number as a string.
  
    e.g. "gi|2765613|gb|Z78488.1|PTZ78488" -> "Z78488.1"
    """
    parts = record.id.split("|")
    assert len(parts) == 5 and parts[0] == "gi" and parts[2] == "gb"
    return parts[3].split('.')[0]
    
if __name__ == "__main__":
   main(sys.argv[1:])



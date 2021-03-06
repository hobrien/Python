#!/usr/local/bin/python

import sys
from os import system, path

def main(argv):
  fasta = argv[0]
  phylip = fasta.replace('.fa', '.phy')
  phyml_tree = phylip + '_phyml_tree.txt'
  phyml_stats = phylip + '_phyml_stats.txt'
  tree = fasta.replace('.fa', '.nwk')
  if not path.exists(phylip) or path.getmtime(fasta) > path.getmtime(phylip):
    system("mafft --quiet --preservecase %s |ConvertAln.pl -x fasta -f phyext -o %s -r" % (fasta, phylip))
  if not path.exists(tree) or path.getmtime(fasta) > path.getmtime(tree):
    try:
      if argv[1] == 'fast':
        system("phyml --quiet --no_memory_check -o n -b 0 -i %s" % phylip)
    except IndexError:
      system("phyml --quiet --no_memory_check -i %s" % phylip)
    system("mv %s %s" % (phyml_tree, tree))
    system("rm %s" % phyml_stats)
    system("ColourTree.py -t %s" % tree)
if __name__ == "__main__":
   main(sys.argv[1:])

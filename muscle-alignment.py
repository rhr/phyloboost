from Bio.Align.Applications import MuscleCommandline
from Bio.SeqRecord import SeqRecord
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
import matplotlib.mlab as mlab
from Bio.Alphabet import IUPAC
from StringIO import StringIO
import scipy.stats as spstats
from Bio.Seq import Seq
from Bio import AlignIO
from Bio import SeqIO
import numpy as np
import glob
import csv
import re

def pos_index(per_base_density):
    ## build a list of the index positions to delete from each sequence list of characters
    pos_list = []
    pos_count = 0
    for b in per_base_density:
        if b is 1:
            pos_list.append(pos_count)
        pos_count = pos_count + 1
    return pos_list

def per_align_stats_calc(f, pos_list, raw_lengths, lengths):
    per_align_stats = []
    new_lens = []
    for l in lengths:
        new_lens.append(l - len(pos_list))
    per_align_stats.append(f) #alignment file name
    per_align_stats.append(min(raw_lengths)) #shortest sequence before align
    per_align_stats.append(max(raw_lengths)) #longest sequence before align
    per_align_stats.append(sum(raw_lengths)/len(raw_lengths)) # mean length of sequence before trim
    per_align_stats.append(np.median(raw_lengths)) #median length of sequence before align
    per_align_stats.append(np.var(raw_lengths)) #variance of pre-trim lengths
    per_align_stats.append(max(lengths)) #alignment length before trim
    per_align_stats.append(max(new_lens)) # alignment length after trim
    per_align_stats.append(len(pos_list)) # number of bases trimmed  
    per_align_stats.append(float(len(pos_list))/float(max(lengths))) # percentage of bases trimmed
    
    return per_align_stats

def parse_config():
    config_params = [];
    config = open('private/config', 'r') 
    for line in (line for line in config if not line.startswith('###')):
        line = line.rstrip('\n')
        line = line.split("=")
        config_params.append (line[1])

    return config_params


## a few import variables

## Gather import configuration information from the config file
params = parse_config() # retreive the params from the config file

density = 0.50
all_lengths = []
plot_stats = []
all_lengths = []
per_bases_cut = []
all_del_bases = []
all_trim_lengths = []
all_stats = []
den_removed_bases = []

##get list of all new fasta files
print "\n\nGetting a list of FASTA files..."
fasta_files = glob.glob("".join([params[7],"fasta/*.fasta"])) # get a list of all fasta files in /fasta
file_count = len(fasta_files)
print "%s files successful found.\n" %file_count



## iterate through each file doing the following:
for f in fasta_files:
    raw_lengths = []
    handle = open(f, "rU")
    for record in SeqIO.parse(handle, "fasta") :
        raw_lengths.append(len(record.seq))
    handle.close()
    
    print "Aligning FASTA file %s" % f
    muscle_cline = MuscleCommandline(input=f, maxiters=2, maxtrees=1)
    stdout, stderr = muscle_cline()
    align = AlignIO.read(StringIO(stdout), "fasta")
    lengths = []
    for a in align:
        lengths.append(len(a.seq))

    character_score = []

    max_len = max(lengths)
    all_lengths.append(max_len) #assign for later use in scatter plot

    ## calculate the amount of missing data for entire alignment
    missing_len = 0
    total_len = 0
    missing_data = 0
    for a in align:
        missing_len = missing_len + a.seq.count('-')
        total_len = total_len + len(a.seq)

    missing_data = float(missing_len)/float(total_len)

    print "Removing bases with less than %s density." % density
    ## Calculate density score for each column of the alignment
    num_records = len(align)
    per_base_density = []

    count = 0
    while count < max_len:
        den_count = 0
        for a in align:
            if a.seq[count] == "-":
                den_count = den_count + 1
        if den_count >= (density*num_records):
            per_base_density.append(1)
        else:
            per_base_density.append(0)
        count = count + 1

        
    ## convert the entire record into a list of records, each containing a list of id and sequence
    file_list = []
    for a in align:
        record_list = []
        #build record list
        record_list.append(str(a.id))
        record_list.append(str(a.seq))
        #append to large list
        file_list.append(record_list)

    ## convert the record.seq object to a list of characters for mainpulation
    char_list = []
    for a in align:
        char_list.append(list(str(a.seq)))

    ## calculate the density of all bases to be removed
    for p in per_base_density:
        if p == 1:
            den_count = 0
            for c in char_list:
                if c[p] is "-":
                    den_count = den_count + 1
            den_removed_bases.append(float(den_count)/float(len(char_list)))
    
    ## traverse the pos_index_list and remove the indexed character from each char_list starting with the highest index
    pos_list = pos_index(per_base_density)
    for p in reversed(pos_list):
        for c in char_list:
            del c[p]

    ## convert list to a seqrecord object for easier manipulation
    count = 0
    record_list = []
    for c in char_list:
        seq_string = "".join(c)
        file_list[count][1] = seq_string
        record = SeqRecord(Seq(seq_string, IUPAC.unambiguous_dna), id=file_list[count][0], name=file_list[count][0], description=file_list[count][0])
        record_list.append(record)
        count = count + 1
    
    all_trim_lengths.append(len(record_list[0].seq))

    ## write list of seq_records to fasta file
    clean_file_id = re.search('fasta/(.+?).fasta', f).group(1)
    alignment_file = "".join([params[6],"alignments/den_",str(density),"_",clean_file_id,".alignment.fasta"])
    SeqIO.write(record_list, alignment_file, "fasta") #after done with all iterations, write the good seq record list to the same file we started with
    
    ## gather information for basic summary stats
    per_align_stats = per_align_stats_calc(f, pos_list, raw_lengths, lengths)
    per_align_stats.append(np.mean(den_removed_bases))
    per_align_stats.append(missing_data)
    per_align_stats.append(pos_list)
    all_stats.append(per_align_stats)
    per_bases_cut.append(per_align_stats[8])


## create stats label
label_list = ["File", "Min Pre Align", "Max Pre Align", "M Len Pre Align", "Mdn Len Pre Align", "Var Pre Align", "Pre Trim Align Len", "Post Trim Aign Len", "Trim Size", "Trim Percentage", "Avg Den Trimmed Bases", "Per Missing Data", "Bases Trimmed"]
all_stats.insert(0, label_list)
##code here to write it all to a file
#print all_stats
stats_filename = "".join(["sum-stats-",str(density),".csv"])
with open(stats_filename, "wb") as ss:
    writer = csv.writer(ss)
    writer.writerows(all_stats)
ss.close()


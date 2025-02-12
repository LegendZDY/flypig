#!/usr/bin/python3
# -*- coding: utf-8 -*-
__author__ = "legendzdy@dingtalk.com"
"""
Author: legendzdy@dingtalk.com
Data: 20250210
Description:
This Script of raw fq data from Legendzdy.  Of course, this means there's a possibility
for other ways.Use at your own discretion.
"""

import re
import gzip
import pysam
from collections import defaultdict

class form_reads_get_modifications:
    """
    from reads get modifications
    Args:
        inputFq: input fq file
        samFile: sam file or bam file
        bedFile: single base annotaiton bed file
        output: output file
        pvalue: pvalue cutoff for modification
    """
    
    MOD_MAP = {
        'A+a': re.compile(r'A'),
        'A+17596': re.compile(r'A'),
        'T+17802': re.compile(r'T'),
        'C+m': re.compile(r'C')
    }
    
    BASE_MAP = {
        "A": ["A", "T"],
        "T": ["T", "A"],
        "C": ["C", "G"]
    }

    def __init__(self, inputFq, samFile, bedFile, output, pvalue=0.98):
        self.inputFq = inputFq
        self.samFile = samFile
        self.bedFile = bedFile
        self.output = output
        self.pvalue = pvalue

    def get_annotation(self):
        def read_bed_file():
            with open(self.bedFile, 'r') as f:
                for line in f:
                    line = line.strip().split("\t")
                    gid = line[0] + ":" + line[1]
                    enst = line[3]
                    base = line[4]
                    yield gid, (enst, base)
        return dict(read_bed_file())

    def find_poslist(self, modList):
        counter = 0
        posList = []
        for mod in modList:
            counter += int(mod)
            posList.append(counter)
            counter += 1
        return posList

    def find_read_position(self, mm, baseList, mlNum):
        modList = mm.split(",")[1:]
        posList = self.find_poslist(modList)
        mlcount = 0
        readPos = []
        readPosPvalue = []
        for pos in posList:
            rpos = baseList[pos]
            pvalue = round(int(mlNum[mlcount])/255, 3)
            readPos.append(rpos)
            readPosPvalue.append(pvalue)
            mlcount += 1
        return readPos, readPosPvalue

    def get_mod_position_with_read(self):
        rpos_mod = defaultdict(list)
        with gzip.open(self.inputFq, 'rt') as f:
                while True:
                    try:
                        name = next(f).strip()
                        seq = next(f).strip()
                        plus = next(f).strip()
                        qual = next(f).strip()
                        
                        namelist = name.split("\t")
                        id = namelist[0].split("@")[-1]
                        MMtagList = namelist[-2].split("MM:Z:")[-1].split(";")
                        MLtag = namelist[-1].split(",")[1:]
                        mlstart = 0
                        for mm in MMtagList:
                            mmlen = len(mm.split(","))
                            if mmlen > 1:
                                mlend = mlstart + mmlen - 1
                                mlNum = MLtag[mlstart:mlend]
                                mlstart += mmlen - 1
                            for mod, base in self.MOD_MAP.items():
                                if mm.startswith(mod):
                                    base_list = [match.start() + 1 for match in base.finditer(seq)]
                                    readPos, readPosPvalue = self.find_read_position(mm, base_list, mlNum)
                                    for rpos, pvalue in zip(readPos, readPosPvalue):
                                        if pvalue >= self.pvalue:
                                            rpos_mod[id].append((rpos, pvalue, mod))
                    except StopIteration:
                        break
        return rpos_mod


    def get_mod_position_with_sam(self):
        rpos_mod = self.get_mod_position_with_read()
        annot = self.get_annotation()
        with open(self.output, "w") as f:
            for read in pysam.AlignmentFile(self.samFile, "r"):
                if not read.is_unmapped and rpos_mod.get(read.query_name) is not None:
                    pos = read.reference_start
                    read_pos = 1
                    strand = "-" if read.is_reverse else "+"
                    for op, length in read.cigartuples:
                        if op == 0:
                            for i in range(length):
                                mod_list = rpos_mod[read.query_name]
                                for rpos, pvalue, mod in mod_list:
                                    if rpos == read_pos + i:
                                        genome_id = f"chr{read.reference_name}:{pos + i}"
                                        if annot.get(genome_id) is not None:
                                            enst, base = annot[genome_id]
                                            rbase = mod[0]
                                            if rbase in self.BASE_MAP and base in self.BASE_MAP[rbase]:
                                                f.write(f"chr{read.reference_name}\t{pos + i}\t{pos + i + 1}\t{pvalue}\t{enst}\t{strand}\t{mod}\t{base}\n")
                            pos += length
                            read_pos += length
                        elif op == 1:  # I: 插入
                            # 插入的碱基在参考基因组上不占位置，但在 read 上有位置
                            read_pos += length
                        elif op == 2:  # D: 删除
                            # 删除的碱基在参考基因组上仍占位置，但跳过它们
                            pos += length
                        elif op == 4:  # S: 跳过
                            # 跳过的碱基不占基因组位置，但在 read 上有位置
                            read_pos += length
                        elif op == 5:  # H: 硬剪切
                            # 硬剪切不占基因组位置
                            read_pos += length
                        else:
                            print(f"op: {op}, length: {length} not supported")
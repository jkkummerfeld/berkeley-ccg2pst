# Berkeley CCG to PST converter

This software converts Combinatory Categorial Grammar (CCG) derivations to Phrase Structure Trees (PST).  For a full description of the method, and discussion of results, see:

[Robust Conversion of CCG Derivations to Phrase Structure Trees](https://aclweb.org/anthology/P/P12/P12-2021.pdf),
Jonathan K. Kummerfeld, James R. Curran and Dan Klein,
ACL (short) 2012

To use the system, download it one of these ways, and run as shown below:

- [Download .zip](https://github.com/jkkummerfeld/berkeley-ccg2pst/zipball/master)
- [Download .tar.gz](https://github.com/jkkummerfeld/berkeley-ccg2pst/tarball/master)
- `git clone https://github.com/jkkummerfeld/berkeley-ccg2pst.git`

If you use my code in your own work, please cite the paper:

```
@InProceedings{Kummerfeld-Klein-Curran:2012:ACL,
  author    = {Jonathan K. Kummerfeld  and  Dan Klein  and  James R. Curran},
  title     = {Robust Conversion of {CCG} Derivations to Phrase Structure Trees},
  booktitle = {Proceedings of the 50th Annual Meeting of the Association for Computational Linguistics (Volume 2: Short Papers)},
  month     = {July},
  year      = {2012},
  address   = {Jeju Island, Korea},
  pages     = {105--109},
  software  = {http://github.com/jkkummerfeld/berkeley-ccg2pst/},
  url       = {http://www.aclweb.org/anthology/P12-2021},
}
```

## Running the code

On a sample of CCGbank:
```
./src/convert.py sample.gold_ptb sample.ccgbank -print_comparison -prefix=sample.ccgbank -verbose -method=markedup ./src/markedup
```

On a sample of C&C Parser output:
```
./src/convert.py sample.gold_ptb sample.candc -print_comparison -prefix=sample.candc -verbose -method=markedup ./src/markedup
```

Conversion output will be in:
```
sample.ccgbank.auto
sample.candc.auto
```

The code also comes with a sample of parses from the Penn Treebank section 00,
the corresponding parses from CCGbank section 00, and the C&C parser output on
the same sentences.

The src directory contains all of the python files required to execute
convert.py and the instruction sets for categories (in markedup).

#!/opt/local/bin/python3.3

import shutil, re, sys, os
import argparse, json, glob, logging
import subprocess, urllib, tempfile, hashlib, time
import functools, itertools, collections
import os.path as path

# from prettytable import PrettyTable
# import prettytable
from itertools import islice, zip_longest

if __name__ != '__main__':
    from ntm.Tools.Project import *
else:
    from Project import *

## Tabulate
## <https://pypi.python.org/pypi/tabulate>

import tabulate

## Pandoc Tables

PANDOC_TABLE_DOCS = """

# Tables

Four kinds of tables may be used. The first three kinds presuppose the use of a 
fixed-width font, such as Courier. The fourth kind can be used with 
proportionally spaced fonts, as it does not require lining up columns.

## Extension: table_captions

A caption may optionally be provided with all 4 kinds of tables (as illustrated 
in the examples below). A caption is a paragraph beginning with the string 
Table: (or just :), which will be stripped off. It may appear either before or 
after the table.

## Extension: simple_tables

Simple tables look like this:


      Right     Left     Center     Default
    -------     ------ ----------   -------
         12     12        12            12
        123     123       123          123
          1     1          1             1

    Table:  Demonstration of simple table syntax.


The headers and table rows must each fit on one line. Column alignments are 
determined by the position of the header text relative to the dashed line below 
it:3

- If the dashed line is flush with the header text on the right side but extends 
    beyond it on the left, the column is right-aligned.
- If the dashed line is flush with the header text on the left side but extends 
    beyond it on the right, the column is left-aligned.
- If the dashed line extends beyond the header text on both sides, the column is 
    centered.
- If the dashed line is flush with the header text on both sides, the default 
    alignment is used (in most cases, this will be left).
- The table must end with a blank line, or a line of dashes followed by a blank 
    line.

The column headers may be omitted, provided a dashed line is used to end the 
table. For example:

    -------     ------ ----------   -------
         12     12        12             12
        123     123       123           123
          1     1          1              1
    -------     ------ ----------   -------

When headers are omitted, column alignments are determined on the basis of the 
first line of the table body. So, in the tables above, the columns would be 
right, left, center, and right aligned, respectively.

## Extension: multiline_tables

Multiline tables allow headers and table rows to span multiple lines of text 
(but cells that span multiple columns or rows of the table are not supported). 
Here is an example:

    -------------------------------------------------------------
     Centered   Default           Right Left
      Header    Aligned         Aligned Aligned
    ----------- ------- --------------- -------------------------
       First    row                12.0 Example of a row that
                                        spans multiple lines.

      Second    row                 5.0 Here's another one. Note
                                        the blank line between
                                        rows.
    -------------------------------------------------------------

Table: Here's the caption. It, too, may span multiple lines.

These work like simple tables, but with the following differences:

They must begin with a row of dashes, before the header text (unless the 
headers are omitted).
They must end with a row of dashes, then a blank line.
The rows must be separated by blank lines.
In multiline tables, the table parser pays attention to the widths of the 
columns, and the writers try to reproduce these relative widths in the output. 
So, if you find that one of the columns is too narrow in the output, try 
widening it in the markdown source.

Headers may be omitted in multiline tables as well as simple tables:


    ----------- ------- --------------- -------------------------
       First    row                12.0 Example of a row that
                                        spans multiple lines.

      Second    row                 5.0 Here's another one. Note
                                        the blank line between
                                        rows.
    ----------- ------- --------------- -------------------------

    : Here's a multiline table without headers.


It is possible for a multiline table to have just one row, but the row should 
be followed by a blank line (and then the row of dashes that ends the table), 
or the table may be interpreted as a simple table.


## Extension: grid_tables

Grid tables look like this:


    : Sample grid table.

    +---------------+---------------+--------------------+
    | Fruit         | Price         | Advantages         |
    +===============+===============+====================+
    | Bananas       | $1.34         | - built-in wrapper |
    |               |               | - bright color     |
    +---------------+---------------+--------------------+
    | Oranges       | $2.10         | - cures scurvy     |
    |               |               | - tasty            |
    +---------------+---------------+--------------------+


The row of =s separates the header from the table body, and can be omitted for 
a header-less table. The cells of grid tables may contain arbitrary block 
elements (multiple paragraphs, code blocks, lists, etc.). Alignments are not 
supported, nor are cells that span multiple columns or rows. Grid tables can be 
created easily using Emacs table mode.

## Extension: pipe_tables

Pipe tables look like this:


    | Right | Left | Default | Center |
    |------:|:-----|---------|:------:|
    |   12  |  12  |    12   |    12  |
    |  123  |  123 |   123   |   123  |
    |    1  |    1 |     1   |     1  |

      : Demonstration of pipe table syntax.


The syntax is the same as in PHP markdown extra. The beginning and ending pipe 
characters are optional, but pipes are required between all columns. The colons 
indicate column alignment as shown. The header can be omitted, but the 
horizontal line must still be included, as it defines column alignments.

Since the pipes indicate column boundaries, columns need not be vertically 
aligned, as they are in the above example. So, this is a perfectly legal 
(though ugly) pipe table:


    fruit| price
    -----|-----:
    apple|2.05
    pear|1.37
    orange|3.09


The cells of pipe tables cannot contain block elements like paragraphs and 
lists, and cannot span multiple lines. Note also that in LaTeX/PDF output, the 
cells produced by pipe tables will not wrap, since there is no information 
available about relative widths. If you want content to wrap within cells, use 
multiline or grid tables.

Note: Pandoc also recognizes pipe tables of the following form, as can produced 
by Emacs’ orgtbl-mode:


    | One | Two   |
    |-----+-------|
    | my  | table |
    | is  | nice  |


The difference is that + is used instead of |. Other orgtbl features are not 
supported. In particular, to get non-default column alignment, you’ll need to 
add colons as above.


"""

def mdBlock(text):
    return "\n{text}\n\n\n".format(text=str(text).strip())

def mdHeader(level, text, postfix=True):
    tag = '#'*level
    postTag = tag if postfix else ''
    return mdBlock('{prefix} {text} {postfix}'.format(prefix=tag, text=text, postfix=postTag))


class TableValue(collections.namedtuple('_TableValue', 'table sources')):
    def format(self):
        return '\n' + str(self.table) + '\n\n' + '\n'.join(self.sources) + '\n'

    def __str__(self):
        return self.format()

## Main
class MarkdownTable(object):

    def __init__(self, **kwargs):
        self.data = []
        self.tabulateOptions = dict()
        self.tabulateOptions.update(kwargs)
        # self.headers = [ h for h in headers ]
        
    # tabulate | pandoc
    # ---------|---------
    # grid     | grid
    # orgtbl   | org_tbl
    
    tablefmts = ["plain", "simple", "grid", "pipe", "orgtbl", "rst", "mediawiki", "latex", "latex_booktabs"]
    
    @classmethod
    def tableTemplate(cls, data, tablefmt='simple', headers=[], numalign="right", floatfmt=".2f", **kwargs):
        
        if not tablefmt in cls.tablefmts:
            raise Exception("Style `%s` not in available styles: %s"%(style, cls.styles))
        
        kwargs.update(dict(numalign="right", floatfmt=".2f"))
        return tabulate.tabulate(data, tablefmt=tablefmt, headers=headers, **kwargs)
    
    def add_row(self, data):
        """docstring for add_row"""
        self.data.append(data)        
        return self
        
    def add_rows(self, data):
        """docstring for add_rows"""
        for row in data: 
            self.data.append(row)        
        return self
        
    def add_items(self, *items):
        """docstring for addRow"""
        self.data.append(items)        
        return self
        
    def _options(self, headers, columns, **kwargs):
        """ handle parsing public api options. """
        # debug(headers)
        
        if headers: kwargs['headers'] = tuple(headers)
        
        # debug(self.tabulateOptions, kwargs)
        items = dict(self.tabulateOptions.items())
        items.update( kwargs.items() )
        
        tabulateOptions = collections.defaultdict(lambda x: '')
        tabulateOptions.update(items)
        
        columns = len(tabulateOptions['headers']) if 'headers' in tabulateOptions else columns
        
        return (columns, headers, tabulateOptions)
        
    def generateTable(self, columns=1, headers=None, **kwargs):
        columns, headers, tabulateOptions = self._options(headers=headers, columns=columns, **kwargs)
        
        # debug(self.data, columns)
        # debug([ i for i in grouper(columns, self.data, '')])
        # table = self.tableTemplate( grouper(columns, self.data, ''), **tabulateOptions)
        table = self.tableTemplate( self.data, **tabulateOptions)
        return TableValue(table, '')
    
class ImageTable(MarkdownTable):
    
    ImageInfo = collections.namedtuple('ImageInfo', 'name imgUrl absPath')
    # _TableValue = 

    import glob
    
    def hasher(obj):
        return hashlib.md5(str(obj).encode('ascii')).hexdigest()[:5]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.images = list()
        

    def addImageGlob(self, *pathGlob):
        pathGlob = os.sep.join(pathGlob) 
        self.addImages(glob.glob(pathGlob))
        return self
        
    def addImages(self, images):
        """ add images from which to generate images. """        
        for imgPath in images:
            self.images.append(self.parseImagePath(str(imgPath)))
        return self
        
    def parseImagePath(self, imgPath):
    
        name = path.splitext(path.basename(imgPath))[0]
        absPath = path.abspath(imgPath)
        imgUrl = urllib.parse.quote(imgPath)
        return self.ImageInfo(name=name, imgUrl=imgUrl, absPath=absPath)
    
    def mdFormat(self, imageInfo, baseDirectory, prefix, suffix):
        """ Format link and source into mdformat """
        
        # assert baseDirectory[-1] == os.sep
        name = "{}{}{}".format(prefix, imageInfo.name, suffix)
        
        # debug(imageInfo.imgUrl, baseDirectory, '')
        path = imageInfo.imgUrl.replace(baseDirectory, '')
        
        mdLink = "![{name}]".format(name=name)
        mdSource = "[{name}]: {path}".format(name=name, path=path)
        
        return (mdLink, mdSource)
        
    def setTabulateOptions(self, **kwargs):
        self.tabulateOptions.update(kwargs)
        
    def generateTable(self, columns=1, headers=None, prefix=hasher, suffix='', directory='', **kwargs):
        columns, headers, tabulateOptions = self._options(headers=headers, columns=columns, **kwargs)
        
        sources = []
        prefix = (prefix(hash(time.time())) if callable(prefix) else prefix)
        suffix = (suffix(hash(time.time())) if callable(suffix) else suffix)

        if prefix: prefix = prefix + '_' 
        if suffix: suffix = '_' + suffix 

        # make sure to append extra '/' for leading path stripping to work 
        base = urllib.parse.quote(path.abspath(directory))+os.sep if directory else ''
        
        mdFormatFunc = functools.partial(self.mdFormat, prefix=prefix, suffix=suffix, baseDirectory=base)
        # debug(self.images)
        
        if not self.images:
            return ('', '')
        
        imgLinks, imgSources = zip( *map(mdFormatFunc, self.images) )

        sources = list(imgSources)
        table = self.tableTemplate( grouper(columns, imgLinks, ''), **tabulateOptions)
            
        return TableValue(table, sources)
        

def main():
    """main function"""
    
    it = ImageTable()
    
    with tempfile.TemporaryDirectory() as tempDir:
        pngs = [ open(str(tempDir)+os.sep+'image'+str(i)+'.png', 'w') for i in range(1,5) ]
        
        imgs = glob.glob(tempDir+os.sep+'*.png') 
        print('\n\t','\n\t'.join(imgs))

        print()
        
        print("##", "Image Tables")

        it1 = ImageTable()        
        it1.addImages(imgs)
        
        ## 
        print("\n###", "Image Tables 1")
        tb1 = it1.generateTable(prefix='table1')
        print(tb1)

        htb1 = hashlib.md5(str(tb1.table).strip().encode('utf-8')).hexdigest()
        print("md5sum", htb1)
        # assert str(htb1) == '6389de8be02beeb3f2abb8ac8d3c378e'

        ## 
        print("\n###", "Image Tables 2")
        tb1 = it1.generateTable(columns=2, prefix='2columns')
        print(tb1.format())

        htb1 = hashlib.md5(str(tb1.table).strip().encode('utf-8')).hexdigest()
        print("md5sum", htb1)
        # assert str(htb1) == '25736c03e346addc4938c8c6b6793ddd'

        ## 
        print("\n###", "Image Tables Ref")
        tb1 = it1.generateTable(directory=tempDir, prefix='refDir')
        print(tb1.format())

        htb1 = hashlib.md5(str(tb1.table).strip().encode('utf-8')).hexdigest()
        print("md5sum", htb1)
        # assert str(htb1) == '52bab9c0d502dcf7d45ba17f9b942065'

        ## 
        print("\n###", "Image Tables Headers")
        headers=['Images', 'Images (Col2)', 'Images (Col3) and Some really long stuff']

        tb1 = it1.generateTable(prefix='headers', headers=headers)        
        print(tb1.format())

        htb1 = hashlib.md5(str(tb1.table).strip().encode('utf-8')).hexdigest()
        print("md5sum", htb1)
        # assert str(htb1) == '90360b4f4f41ed0b17f24217a11d369a'
        
        ##
        print("\n###", "Image Tables Grid")
        tb1 = it1.generateTable(headers=['Images', 'Images (Col2)', 'Images (Col3) '], tablefmt='grid', prefix='grid')
        print(tb1.format())

        htb1 = hashlib.md5(str(tb1.table).strip().encode('utf-8')).hexdigest()
        print("md5sum", htb1)
        # assert str(htb1) == '91d450220849f08889c8c6cebf6cd01c'
        

        
        
    
    
    
if __name__ == '__main__':
    main()
    
    
    
    
    
    
    
    
    
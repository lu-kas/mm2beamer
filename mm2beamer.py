import ntpath
import xml.etree.ElementTree as ET
import sys
import re

def startTexEnv(env, opt=None):
    if opt:
        optstr = "[%s]"%opt
    else:
        optstr = ""
        
    return "\\begin{%s}%s\n"%(env, optstr)

def stopTexEnv(env):
    return "\\end{" + env + "}\n"

def checkRemoveCommand(node, command):
    posa = node.attrib['TEXT'].find("#"+command)
    if posa >= 0:
        posb = node.attrib['TEXT'].find("#", posa+1)
        fullcommand = node.attrib['TEXT'][posa:posb+1]
        node.attrib['TEXT'] = node.attrib['TEXT'].replace(fullcommand, "", 1)
        offset = 1
        while (any(fullcommand[offset+len(command)] in s for s in [' ', '\n'])) and (offset+len(command)+1) < len(fullcommand): 
            offset+=1
        return fullcommand[offset+len(command):-1]    
    return None

def checkRemoveMarker(node, marker):
    text = node.attrib['TEXT']
    pos = text.find(marker, 0, len(marker))
    if pos == 0:
        node.attrib['TEXT'] = node.attrib['TEXT'].replace(marker, "")
        return True
    return False

def getTexContent(node):
    
    text = node.attrib['TEXT'].encode('UTF-8')
    res = ""
    
    #output equation
    eqs = node.findall(".//hook[@EQUATION]")
    for eq in eqs:
            equation = eq.attrib['EQUATION']
            res += "\\begin{equation}\n"
            res += equation + "\n"
            res += "\\end{equation}\n"
    if eqs != []:
    	return res
            
    #output figure
    figs = node.findall(".//hook[@URI]")
    for fig in figs:
            
            figure = fig.attrib['URI']
            scale = "0.7"
            label = "none"
            
            meta_raws = node.findall("./node")
            for meta_raw in meta_raws:
            	meta = meta_raw.attrib['TEXT'].encode('UTF-8')

            	if meta.startswith("scale:"):
            		scale = meta[6:]
            	if meta.startswith("label:"):
            		label = "fig:" + meta[6:].strip()
            
            res = startTexEnv("figure") + \
	          		"\\includegraphics[width=" + scale + "\\columnwidth]{" + figure + "} \n" + \
            		"\caption{" + text + "} \n" + \
            		"\label{" + label + "} \n" + \
            		stopTexEnv("figure")
            print res
    if figs != []:
    	return res
    
    #equation node
    if text.startswith("\latex"):
        equation = text[6:]
        res  = "\\begin{equation}\n"
        res += equation + "\n"
        res += "\\end{equation}\n"
        return res
    
    #center line
    cl = checkRemoveCommand(node, "CL")
    if cl != None:
        cltext = node.attrib['TEXT'].encode('UTF-8')
        res = "\\centerline{%s}"%cltext
    	return res

	#output simple text
    text = node.attrib['TEXT'].encode('UTF-8')
    res = text + "\n"
    return res


    
#####################################################################

def processSlideNodes(section_node):
	slide_nodes = section_node.findall("node")
	for slide in slide_nodes:
		print "found slide  : ", slide.attrib['TEXT']


		title = slide.attrib['TEXT'].encode('UTF-8')
		print "slide: ", title

		section = checkRemoveCommand(slide, "SEC")
		if section != None:
			of.write("\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n")
			of.write("\\part{"+section+"}\n")
			of.write("\\frame{\\partpage}\n")
			continue

		of.write("\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n")
		of.write(startTexEnv("frame", "fragile"))
		of.write("\\frametitle{"+title+"}\n")

		columns = False
		itemize = False
		enumerate = False

		contents = slide.findall(".node")

		for content in contents:
	
			## check for itemization item
			if checkRemoveMarker(content, "* "):

				if not itemize:
					if enumerate:
						enumerate = False
						of.write(stopTexEnv("enumerate"))
				
					itemize = True
					of.write(startTexEnv("itemize"))  
		
				of.write("  \\item ")# + getTexContent(content) + "\n")

			elif itemize:
				itemize = False
				of.write(stopTexEnv("itemize"))
		
			## check for enumeration item
			resume = checkRemoveCommand(content, "RESUME")
			cont_enum = checkRemoveCommand(content, "CE")
			if checkRemoveMarker(content, "1. "):
		
				if not enumerate:
					if itemize:
						itemize = False
						of.write(stopTexEnv("itemize"))
				
					enumerate = True
					of.write(startTexEnv("enumerate"))
					if resume != None:
						of.write(r"\setcounter{enumi}{%s}"%resume)
		
				of.write("  \\item ")# + getTexContent(content) + "\n")

			elif enumerate and (cont_enum==None):
				enumerate = False
				of.write(stopTexEnv("enumerate"))

	
			figure=checkRemoveCommand(content, "FIG")
			if figure != None:
				figscale=checkRemoveCommand(content, "SCALE")

				if not figscale: figscale = "0.9"

				of.write("\\centerline{\\includegraphics[width=" + figscale + "\\columnwidth]{" + figure + "}}\n")
	
			listing=checkRemoveCommand(content, "LST")
			if listing != None:
				of.write(r"\lstinputlisting[title=%s]{%s}"%(ntpath.basename(listing), listing))
	
			code=checkRemoveCommand(content, "CODE")
			code_noline=checkRemoveCommand(content, "CODE_NOLINE")        
			if code != None:
	#            of.write(startTexEnv("lstlisting", r"frame=leftline, basicstyle=\small\ttfamily, numbers=none"))
				if code_noline==None:
					of.write(startTexEnv("lstlisting"))
				else:
					of.write(startTexEnv("lstlisting", r"numbers=none"))
				of.write(code)
				of.write(stopTexEnv("lstlisting"))            

			shell=checkRemoveCommand(content, "SHELL")
			if shell != None:
				of.write(startTexEnv("lstlisting", r"numbers=none"))
				of.write(shell)
				of.write(stopTexEnv("lstlisting"))            

	
			column = checkRemoveCommand(content, "SC")
			if column != None:
				if not columns:
					columns = True
					of.write(startTexEnv("columns"))
				else:
					of.write(stopTexEnv("column"))
		
				if column == "": column = "0.5"
			
				of.write("\n" + startTexEnv("column}{" + column + "\\textwidth"))
		
			column_end = checkRemoveCommand(content, "EC")
			if column_end != None:
				if columns:
					columns = False
					of.write(stopTexEnv("column"))
					of.write(stopTexEnv("columns"))
	
			vspace = checkRemoveCommand(content, "VS")
			if len(content) == 0: vspace = "0.025"
			if vspace != None:
				if vspace == "": vspace = "0.05"
				of.write("\n\\vspace{%s\\textwidth}\n"%vspace)
	
			footline = checkRemoveCommand(content, "FL")
			if footline != None:
				of.write("\n\\vskip0pt plus 1filll \n {\\tiny " + footline.encode('UTF-8') + "}")
	
			## simple text
			#if (itemize == False and enumerate == False):
			of.write(getTexContent(content) + "\n\n")

		if itemize:
			of.write(stopTexEnv("itemize"))
	
		if enumerate:
			of.write(stopTexEnv("enumerate"))

		if columns:
			of.write(stopTexEnv("column"))
			of.write(stopTexEnv("columns"))

		of.write(stopTexEnv("frame"))


#####################################################################
#####################################################################
#####################################################################

tree = ET.parse(str(sys.argv[1]))
root = tree.getroot()

of = open(str(sys.argv[2]), 'w')

nodes = root.findall("*/node")
slides = []

lec_no = 0
if len(sys.argv) > 3:
    lec_no = int(sys.argv[3])
    print "preparing slides for lecture %d"%int(lec_no)

global_author = 'no author name'
global_title = 'no title'
global_date = 'today'
global_type = 'lecture'

print "-- reading global attributes"
for att_nodes in root.findall("./node/attribute"):
	if att_nodes.attrib['NAME'] == 'author': global_author = att_nodes.attrib['VALUE']
	if att_nodes.attrib['NAME'] == 'title': global_title = att_nodes.attrib['VALUE']	
	if att_nodes.attrib['NAME'] == 'date': global_date = att_nodes.attrib['VALUE']		
	if att_nodes.attrib['NAME'] == 'type': global_type = att_nodes.attrib['VALUE']	

print " - author: ", global_author
print " - title : ", global_title
print " - date  : ", global_date
print " - type  : ", global_type


if (global_type != 'talk'):
	for chapter_node in nodes:
		print "found chapter: ", chapter_node.attrib['TEXT']

		of.write("\\section{%s}\n"%chapter_node.attrib['TEXT'])

		#of.write("\\frame{\\tableofcontents[sectionstyle=show/show,subsectionstyle=show/show/hide]}\n")	
		of.write("\\frame{\\tableofcontents[sectionstyle=show/hide,subsectionstyle=show/show/hide]}\n")
	
		section_nodes = chapter_node.findall("node")
		for section_node in section_nodes:
		
			print "found section: ", section_node.attrib['TEXT']
		
			of.write("\\subsection{%s}\n"%section_node.attrib['TEXT'])
			of.write("\\frame{\\tableofcontents[sectionstyle=show/hide,subsectionstyle=show/shaded/hide]}\n")

			processSlideNodes(section_node)
else:

	processSlideNodes(root.findall(".")[0][0])

of.close()

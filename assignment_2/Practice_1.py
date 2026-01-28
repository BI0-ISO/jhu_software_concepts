from urllib.request import urlopen

url = "http://olympus.realpython.org/profiles/aphrodite"

page = urlopen(url)

html_bytes = page.read()

# Get all the html contents of the website

html = html_bytes.decode("utf-8")

print(html)

# Get the index of where < starts for the title section
# Remember that when slicing the last index [:] is not included so asking for [14] vs. [14:15] is the same 

title_index = html.find("<title>")

print(title_index)

print(html[title_index])

# Get the index of where the title string actually starts 

start_index = title_index + len("<title>")

print(html[start_index])

print(start_index)



end_index = html.find("</title>")

print(html[end_index])

print(end_index)

title = html[start_index:end_index]

print(title)


# Trying a more complicated website 

url_2 = "http://olympus.realpython.org/profiles/poseidon"


page_2 = urlopen(url_2)

html_2 = page_2.read().decode("utf-8")

print(html_2)

start_index_2 = html_2.find("<title>") + len("<title>")

print(html_2[start_index_2])

end_index_2 = html_2.find("</title>")

print(html_2[end_index_2])

title_2 = html[start_index_2:end_index_2]

print(title_2)


# Regular Expressions ---------------------------------------


import re

# The string "ab*c" is saying a string "a (zero or more instances of b) c"

m_1 = re.findall("ab*c", "ac")

print(m_1)

m_2 = re.findall("ab*c", "abcd")

print(m_2)

m_3 = re.findall("ab*c", "acc")

print(m_3)

m_4 = re.findall("ab*c", "abcac")

print(m_4)

m_5 = re.findall("ab*c", "abdc")

print(m_5)

m_6 = re.findall("ab*c", "abbbc")

print(m_6)

# By default, pattern matching is case sensistive, thus: 

m_7 = re.findall("ab*c", "ABC")

print(m_7)

m_8 = re.findall("ab*c", "ABC", re.IGNORECASE)

print(m_8)


# As before, * was used to say zero or more instances, while . is used to denote any single character 


m_8 = re.findall("a.c", "abc")
print(m_8)

m_9 = re.findall("a.c", "abbc")
print(m_9)

m_10 = re.findall("a.c", "ac")
print(m_10)

m_11 = re.findall("a.c", "acc")
print(m_11)

# The pattern .* inside a regular expression stands for any character repeated any number of times. 
# For instance, you can use "a.*c" to find every substring that starts with "a" and ends with "c", 
# regardless of which letter—or letters—are in between:

m_12 = re.findall("a.*c", "abc")
print(m_12)

m_13 = re.findall("a.*c", "abbc")
print(m_13)

m_14 = re.findall("a.*c", "ac")
print(m_14)

m_15 = re.findall("a.*c", "acc")
print(m_15)


# Using re.search() vs re.findall()

match_results = re.search("ab*c", "ABC", re.IGNORECASE)
print(match_results.group())

# The regex .* is greedy, so it will grab everything from the first < to the last >, thus losing everything in between 

string = "Everything is <replaced> if it's in <tags>."
string = re.sub("<.*>", "ELEPHANTS", string)

print(string)


# Alternatively, we can use .*? to grab all the instances of <string> and replace them 

string = "Everything is <replaced> if it's in <tags>."
string_2 = re.sub("<.*?>", "ELEPHANTS", string)

print(string_2)

# He is another case with the regex pattern .*?

string = "Everything is <replaced> if it's in <tags> also check this <tested>."
string_3 = re.sub("<.*?>", "ELEPHANTS", string)

print(string_3)

#----------------------------------------------------------

# Now we will use the information we learned about regex patterns and apply it to difficult pages with not so nice htmls 

url = "http://olympus.realpython.org/profiles/dionysus"
page = urlopen(url)
html = page.read().decode("utf-8")

print(html)

# Here we look for everything between the start and end of <title> and </title> 

pattern = "<title.*?>.*?</title.*?>"
pattern_name = "<h2.*?>.*?</h2.*?>"

match_results = re.search(pattern, html, re.IGNORECASE)
title = match_results.group()

match_results_2 = re.search(pattern_name, html, re.IGNORECASE)
title_2 = match_results_2.group()



print(title) 

print(title_2) 


title = re.sub("<.*?>", "", title) # Remove HTML tags

print(title)
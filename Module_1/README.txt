This file was created in case the README.md was not the desired format for the assignemnt. I noticed that the SHALL says README.txt, so I just wanted to have both in case. 



# jhu_software_concepts
This is a repository for Modern Concepts of Python (Spring 2026)

Module 1 Notes ---------------

**Following SSH authenication:** 

I first accessed my "Github-Setup" directory on my local machine 
Following this I used "git clone + SSH" to clone my repo and used "touch Module_1_Solution" to add the file to my computer 
I then used "git add <filename>" to tell Git that I want to stage or include this file in the next commit 
I then wanted to bundle up these changes by using "git commit -m "Added Module 1 Solution""
Following this I take my prepared package and I use "git push" to add it to the main repo (i.e. from my computer to git)

Access Command for code: **python run.py**

**Information for Instructors:** 

- Please enjoy the website and its associated pages! I had an amazing time creating the framework and trying to make everything look nice.
- You should be able to easily access the Home page using the command above and from there it should be a seamless navigation to my About Me page, my Project Repo page, and the page containing              information about the Module 1 Assignment
- If there is anything you feel that could have been coded better or if you feel things should have been organized differently please let me know! I am always excited to learn and provide a better product.  

**Assignment Check List (All SHALLS and SHOULDS):** 

1) Flask was used to make the website framework. You will see that flask must be imported into __init__.py in order for this website to work. Futhermore it is a required installment in "requirements.txt"
   
2) Upon accessing the website after running the command "flask --app Module_1 run" you will have access to the following websites:
   - Home Page: including name, position, bio, and image (bio text has been placed on the left and the image has been placed on the right)
   - Contact Page: Contact information is on my "About" page and includes my hobbies, some fun photos, my LinkedIn profile link, and my email address
   - Project Page: This page is dedicated to storing all my projects for Modern Concepts of Python. Clicking on the project will take you to a new page where the title of the Module 1 project is, a                        little description of the project, some key features of the project, and a link to my GitHub repo.
   
3) At the top right of the "Home" page you will see a navigation bar that will take you to the other pages
   - This navigation bar is at the top right of every page
   - The current tab is highlighted and underlined
   - The tabs are colorized to easily visualize them from the rest of the page
  
4) To start the application download the "requirements.txt" file, which only contains "Flask" at this time, and then cd to the directory "jhu_software_concepts". From here type the command
   **python run.py**

5) You will see that the repo is named "jhu_software_concepts" and that the __init__.py and pages.py files lie inside the Module_1 folder

6) As per the "SHALL" requirement you will see that in "run.py" the program runs at port 8080 and localhost

7) As stated in (4) a "requirements.txt" file is provided to ensure that flask is added to the enviroment

8) Python 3.12 has been used in this assignment

9) This "README.txt" acts as my instructions to operate the sit

10) You will see that in "pages.py" blueprints were used to control multiple different pages

11) You will see that in the "static" folder there are images for the pages and a CSS file to manipulate the overall look of the website (AI was used to create the CSS file)

12) You will see that in the "templates" folder there are html templates for each of the pages (AI was used to create the htmls)

13) The code is commented with clear variables, I am also always happy to answer questions on how I created the framework


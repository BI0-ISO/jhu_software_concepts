import pytest 
import math 
import source.shapes as shapes 


# Note that rectangle is being used twice, this is exhausting 
# To help use lets use fixtures 
# - fixtures seem to act like a global varianle that can be called when need so we 
# -> don't need to keep creating the same variable in each function 

# Note that these fixtures are only global to the script not to other files

# Uncomment the below to see its use in a single script
# -> currently it is commented for the conftest.py file 

# @pytest.fixture

# def my_rectangle (): 
#     return shapes.Rectangle(10,20)


# @pytest.fixture

# def weird_rectangle():
#     return shapes.Rectangle(5,6)





def test_area(my_rectangle):
    #rectangle  = shapes.Rectangle(10, 20)
    assert my_rectangle.area() == 10 * 20 


def test_perimeter(my_rectangle):
    #rectangle  = shapes.Rectangle(10, 20)
    assert my_rectangle.perimeter() == (10 * 2) + (20 * 2)


def test_not_equal(my_rectangle,weird_rectangle):
    assert my_rectangle != weird_rectangle
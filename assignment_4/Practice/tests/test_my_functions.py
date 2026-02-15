import pytest 
import source.my_functions as my_functions 

import time 

# Below we have Function based tests 

def test_add(): 
    result = my_functions.add(1,4)
    assert result == 5

def test_divide(): 
    result = my_functions.divide(10,5)
    assert result == 2


def test_add_strings(): 
     result = my_functions.add("I like ", "burgers")
     assert result == "I like burgers"

def test_divide_by_zero(): 

    # Here we are saying, hey we expect this to cause an error because of 
    # zero division, so it will still pass okay 

    # Additionally, if we know what error will occur from a certain command on our function 
    # -> we can input that error tupe into the below

    #with pytest.raises(ZeroDivisionError):
    with pytest.raises(ValueError):    
        my_functions.divide(10, 0)

    
    # Even though we say this is true we still get a zero divison error 

    #result = my_functions.divide(10,0)
    #assert True 



@ pytest.mark.slow

# Good to use this slow mark when performing long calculations

def test_very_slow(): 

    time.sleep(5)
    result = my_functions.divide(10,5)
    assert result == 2


@ pytest.mark.skip(reason = "This feature is currently broken")

def test_add(): 
    assert my_functions.add(1,2) == 3



@ pytest.mark.xfail(reason = "We know we cannot divde by zero")

def test_divide_zero_broken(): 
    my_functions.divide(4,0) 


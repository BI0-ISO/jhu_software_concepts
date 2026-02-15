import math

class Shape: 

    def area(self): 
        pass

    def perimeter(self): 
        pass 


class Circle(Shape): 

    def __init__(self, radius): 
        # __init__ runs when you create a Circle.
        # It stores the required data (radius) on the instance so area/perimeter work.
        # Without __init__, each Circle wouldn't have a radius unless you set it later.
        self.radius = radius 


    def area(self): 
        return math.pi * self.radius ** 2
    

    def perimeter(self):
        return 2 * math.pi * self.radius 
    

class Rectangle(Shape): 

    def __init__(self, length, width): 
        # __init__ defines the required state for every Rectangle instance.
        # It ensures length and width exist on self so other methods can rely on them.
        self.length = length 
        self.width = width 

    def __eq__(self, other): 
        if not isinstance(other, Rectangle): 
            return False
        
        return self.width == other.width and self.length == other.length

    def area(self): 
        return self.length * self.width
    
    def perimeter(self):
        return (self.length * 2) + (self.width * 2)
    


class Square(Rectangle):

    def __init__(self, side_length):
        # __init__ here sets up Square by delegating to Rectangle with equal sides.
        # This keeps initialization consistent and guarantees length/width exist.
        super().__init__(side_length, side_length)

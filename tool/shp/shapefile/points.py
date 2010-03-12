class Point:
    """
    The point class stores a point with class variables.
    Coordinates can also be accessed using indexing.
    """
    def __init__(self,*args):
        """
        Intialization accepts two numbers or a list with two numbers.
        Points have one x and one y attribute.

        >>> a=Point(1,2)
        >>> a=Point([1,2])
        >>> len(a)
        2
        >>> repr(a)
        '(1, 2)'
        >>> a[1]
        2
        >>> a[-2]
        1
        """
        try:
            if len(args)==2:
                self.x,self.y=args
            elif len(args)==1:
                if len(args[0])==2:
                    self.x,self.y=args[0]
        except:
            raise TypeError, "A point must be initialized with two numbers or a list containing two numbers, recieved"

    def __repr__(self):
        """
        Points are represented as (x,y)
        """
        return str((self.x,self.y))

    def __getitem__(self,i):
        """
        Points can be indexed using positive and negative indicies
        """
        if i==0 or i==-2:
            return self.x
        elif i==1 or i==-1:
            return self.y
        else:
            raise IndexError

    def __len__(self):
        """
        Points instances are always of length 2
        """
        return 2

class LineSegment:
    """
    The LineSegment class stores a line segment with Point type class variables.
    Coordinates can also be accessed using indexing.

    >>> a=LineSegment(0,1,2,3)
    >>> a=LineSegment((0,1),(2,3))
    >>> a=LineSegment(Point(0,1),Point(2,3))
    >>> len(a)
    2
    >>> a[0]
    '(0, 1)'
    >>> a[0][1]
    1
    """
    def __init__(self,*args):
        try:
            if len(args)==4:
                self.a=Point(args[0],args[1])
                self.b=Point(args[2],args[3])
            elif len(args)==2 and len(args[0])==2 and len(args[1])==2:
                self.a=Point(args[0][0],args[0][1])
                self.b=Point(args[1][0],args[1][1])
        except:
            raise TypeError, "A line must be initialized with four numbers or a list containing two pairs of numbers."

    def __repr__(self):
        """
        Line segments are represented as ((x,y),(x,y))
        """
        return str((self.a,self.b))

    def __getitem__(self,i):
        """
        Line segments can be indexed using positive and negative indicies
        """
        if i==0 or i==-2:
            return self.a
        elif i==1 or i==-1:
            return self.b
        else:
            raise IndexError

    def __len__(self):
        """
        Lines segments instances are always of length 2
        """
        return 2
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()

"""Clip a raster image using a shapefile"""

import gdal, gdalnumeric
from osgeo import gdal_array
#import sys

#sys.path.append("D:\project\Python\pyshp-1.2.12\shapefile.py")

import shapefile
import Image, ImageDraw

gdal.UseExceptions()

# Raster image to clip
raster = r"D:\project\Python\PM25.TIF"

# Polygon shapefile used to clip
shp = r"D:\project\Python\clip"

# Name of clipped raster file(s)
output = r"D:\project\Python\out"

def imageToArray(i):
    """
    Converts a Python Imaging Library array to a gdalnumeric image.
    """
    a=gdalnumeric.numpy.fromstring(i.tostring(),'b')
    a.shape=i.im.size[1], i.im.size[0]
    return a

	#
#  EDIT: this is basically an overloaded
#  version of the gdal_array.OpenArray passing in xoff, yoff explicitly
#  so we can pass these params off to CopyDatasetInfo
#
def OpenArray( array, prototype_ds = None, xoff=0, yoff=0 ):
    #ds = gdal.Open( gdalnumeric.GetArrayFilename(array) )
    ds=gdal_array.OpenNumPyArray(array)
    #ds=gdal_array.OpenArray(array)
    if ds is not None and prototype_ds is not None:
        if type(prototype_ds).__name__ == 'str':
            prototype_ds = gdal.Open( prototype_ds )
        if prototype_ds is not None:
            gdalnumeric.CopyDatasetInfo( prototype_ds, ds, xoff=xoff, yoff=yoff )
    return ds

def world2Pixel(geoMatrix, x, y):
  """
  Uses a gdal geomatrix (gdal.GetGeoTransform()) to calculate
  the pixel location of a geospatial coordinate 
  """
  ulX = geoMatrix[0]
  ulY = geoMatrix[3]
  
  print ("ulx %f" %ulX)
  print ("uly %f" %ulY)
  xDist = geoMatrix[1]
  #print xDist
  
  yDist = geoMatrix[5]
  #print yDist 
  rtnX = geoMatrix[2]
  rtnY = geoMatrix[4]
  pixel = int((x - ulX) / xDist)
  line = int((ulY - y) / xDist)
  #line = int((ulY - y) / yDist)
  return (pixel, line) 

# Load the source data as a gdalnumeric array
srcArray = gdalnumeric.LoadFile(raster)

# Also load as a gdal image to get geotransform (world file) info
srcImage = gdal.Open(raster)
geoTrans = srcImage.GetGeoTransform()

# Use pyshp to open the shapefile
r = shapefile.Reader("%s.shp" % shp)

# Convert the layer extent to image pixel coordinates
minX, minY, maxX, maxY = r.bbox
ulX, ulY = world2Pixel(geoTrans, minX, maxY)
lrX, lrY = world2Pixel(geoTrans, maxX, minY)

# Calculate the pixel size of the new image
pxWidth = int(lrX - ulX)
pxHeight = int(lrY - ulY)

# Multi-band image?
#Check this modification in script in: http://karthur.org/2015/clipping-rasters-in-python.html
try:
    clip = srcArray[:, ulY:lrY, ulX:lrX]

# Nope: Must be single-band
except IndexError:
    clip = srcArray[ulY:lrY, ulX:lrX]


# Create a new geomatrix for the image
geoTrans = list(geoTrans)
geoTrans[0] = minX
geoTrans[3] = maxY

# Map points to pixels for drawing the county boundary 
# on a blank 8-bit, black and white, mask image.
pixels = []
for p in r.shape(0).points:
  pixels.append(world2Pixel(geoTrans, p[0], p[1]))
rasterPoly = Image.new("L", (pxWidth, pxHeight), 1)
# Create a blank image in PIL to draw the polygon.
rasterize = ImageDraw.Draw(rasterPoly)
rasterize.polygon(pixels, 0)
# Convert the PIL image to a NumPy array
mask = imageToArray(rasterPoly)   

# Clip the image using the mask
clip = gdalnumeric.numpy.choose(mask, (clip, 0)).astype(gdalnumeric.numpy.uint8)

# Save clipping as tiff
#gdalnumeric.SaveArray(clip, "%s.tif" % output, format="GTiff", prototype=raster)

#
# EDIT: create pixel offset to pass to new image Projection info
#
xoffset =  ulX
yoffset =  ulY

gtiffDriver = gdal.GetDriverByName( 'GTiff' )
if gtiffDriver is None:
    raise ValueError("Can't find GeoTiff Driver")
gtiffDriver.CreateCopy( "OUTPUT.tif",
     OpenArray( clip, prototype_ds=raster, xoff=xoffset, yoff=yoffset )
    )

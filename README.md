# mtkgpkg2svg

`mtkgpkg2svg` is as python script that renders data from the [Topographic Database](https://www.maanmittauslaitos.fi/en/maps-and-spatial-data/expert-users/product-descriptions/topographic-database) (available as open data) of National Land Survey of Finland as svg.

Not for navigational use!

For example to get a render covering some of Nuuksio, try:

~~~
python -m mtkgpkg2svg 6688192.325 363999.331 \
    ./test.svg \
    resources/maastotietokanta_kaikki_Kirkkonummi.gpkg \
    resources/maastotietokanta_kaikki_Vihti.gpkg \
    resources/maastotietokanta_kaikki_Espoo.gpkg
~~~

(You will need to download the three geopackage files from National Land Survey of Finland)

This is a work in progress. For example note that

- The output files are rather large
- Not all types of items in the Topographic Database are rendered 

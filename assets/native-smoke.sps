* Synthetic smoke fixture only not executed or validated against SPSS at creation.
* Run in an isolated directory and inspect all errors warnings and XML values.
SHOW VERSION.
DATA LIST FREE /id x y.
BEGIN DATA
1 0 1
2 1 3
3 2 2
4 3 5
5 4 4
END DATA.
FILTER OFF.
SPLIT FILE OFF.
WEIGHT OFF.
OMS
 /SELECT TABLES
 /DESTINATION FORMAT=OXML OUTFILE='native-smoke-spss.xml'.
DESCRIPTIVES VARIABLES=x y
 /STATISTICS=MEAN STDDEV MIN MAX.
REGRESSION
 /MISSING LISTWISE
 /STATISTICS COEFF R ANOVA CI(95)
 /DEPENDENT y
 /METHOD=ENTER x.
OMSEND.

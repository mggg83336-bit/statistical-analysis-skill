* Synthetic smoke fixture only. Not executed or validated against Stata at creation.
* Run in an isolated directory. Agent must set the confirmed target version if needed.
clear all
set more off
capture log close
log using "native-smoke-stata.log", text replace
about
input long id double x double y
1 0 1
2 1 3
3 2 2
4 3 5
5 4 4
end
isid id
summarize x y, detail
regress y x
matrix list e(b)
matrix list e(V)
display "N=" e(N)
display "df_r=" e(df_r)
display "r2=" %21.16g e(r2)
scalar smoke_N = e(N)
scalar smoke_df = e(df_r)
scalar smoke_r2 = e(r2)
tempname smoke_handle
postfile `smoke_handle' str32 term double(estimate se t df p ci_low ci_high) using "native-smoke-stata-coefficients.dta", replace
foreach term in x _cons {
    scalar smoke_b = _b[`term']
    scalar smoke_se = _se[`term']
    scalar smoke_t = smoke_b / smoke_se
    scalar smoke_p = 2 * ttail(smoke_df, abs(smoke_t))
    scalar smoke_crit = invttail(smoke_df, 0.025)
    post `smoke_handle' ("`term'") (smoke_b) (smoke_se) (smoke_t) (smoke_df) (smoke_p) (smoke_b-smoke_crit*smoke_se) (smoke_b+smoke_crit*smoke_se)
}
postclose `smoke_handle'
generate byte analysis_sample = e(sample)
export delimited id x y analysis_sample using "native-smoke-stata-sample.csv", replace
preserve
use "native-smoke-stata-coefficients.dta", clear
format estimate se t df p ci_low ci_high %24.17g
export delimited using "native-smoke-stata-coefficients.csv", datafmt replace
restore
log close

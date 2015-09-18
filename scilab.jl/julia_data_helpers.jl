
# using PyPlot
using Distributions
using GLM
using Formatting
using MAT;
using Glob;
using Match
# using Memoize
using Pipe
using DataStructures
# using FunctionalData

function fit_weibul(data)


    y = log(sort(data))
    rank = 1:length(data)  # ranks = {1, 2, 3, ... 10}
    median_rank = (rank - 0.3)/(length(rank) + 0.4)
    x = log(-log(1 - median_rank))

    intercept, slope = linreg(x,y)

    shape = 1/slope
    x_intercept = - intercept / shape
    scale = exp(-x_intercept/slope)

#     @show(shape, scale)
    return Weibull(shape, scale)
end

function f2(f)
    @sprintf("%.2f", f)
end

## Array indexes


≈(x,y::Real) = isapprox(x, y)
≈(x,yt::Tuple) = isapprox(x, yt[1], atol=yt[2])
≈(xs::Array,y::Int) = find(x-> trunc(x) == y, xs)
≈(xs::Array,y::Real) = find(x->isapprox(x, y), xs)
≈(xs::Array,yt::Tuple) = find(x->isapprox(x, yt[1], atol=yt[2]), xs)

## Dictionary Handling ##

markdownsplitter(x::String) = @pipe x |> strip(_) |> strip(_,'|') |> split(_,'|') |> map(strip,_)
dictFromArray(fields) = x -> OrderedDict(zip(fields,x))
arrayFromDictKeyArray(d::Dict, keys::Array, exclude...) = [ d[k] for k in filter(x-> !(x in exclude),keys) ]

⊂(d::Dict, keys::Array) = Dict( [ k=>v for (k,v) in filter((x,y)-> in(x,Set(keys)),d) ] )
∪(u::Dict, v::Dict) = Dict( concat(u ⊂ collect(keys(v)),v) )

## Plotting Configs ##

function configure_matplotlib_publication_style()

    ## NSF Grant Settings
    rc("axes", linewidth=2)                                # but this works

    rc("font", size=18, family="serif", variant="normal", weight="heavy", serif=["Times New Roman"])
    rc("text", color="k")
    rc("axes", facecolor="white", color_cycle="k", labelsize= 16, labelcolor= "k", linewidth= 1, edgecolor="k")

    rc("figure", facecolor="white")
    rc("figure", figsize=(6,4))
    rc("savefig", facecolor="white", edgecolor="white", dpi=300)

    rc("figure.subplot", wspace=0.4)

    rc("xtick.major", pad=5)
    rc("ytick.major", pad=5)

    rc("legend", frameon=true, handlelength=1.5)
    rc("text", usetex=false)

    rc("grid", linestyle="-", color="lightgrey" )
    rc("axes", grid = true)
    rc("axes", labelweight="normal" )
    rc("axes.formatter", use_mathtext=false )

    rc("font", weight="normal")
    rc("xtick", labelsize=15)
    rc("ytick", labelsize=15)
    rc("legend", scatterpoints = 1)

    return;
end

using Formatting

f1(f) = fmt(FormatSpec("0.1f"), f)
f2(f) = fmt(FormatSpec("0.2f"), f)
f3(f) = fmt(FormatSpec("0.3f"), f)
e2(f) = fmt(FormatSpec(".2e"), f)
e1(f) = fmt(FormatSpec(".1e"), f)

function ff(f::Real, n::Int=1)
    abs(f) < 1/10^n ? fmt(FormatSpec(".$(n)e"), f) : fmt(FormatSpec(".$(n)f"), f)
end


type HTML
   s::String
end

import Base.writemime

function writemime(io::IO, ::MIME"text/html", x::HTML)
    write(io, x.s);
end


simplify_mat(d::Dict{ASCIIString, Any}) = Dict{Symbol, Any}( [ symbol(string(k)) => simplify_mat(v) for (k,v) in d ] )
simplify_mat(arr::Array{Float64,2}) = arr[:] # slicing???
simplify_mat(o::Any) = o




function convert_slices(matdata)
    # @show(keys(matdata))
    @assert Set(map(x->size(x,1), matdata[:data] |> values)) |> length == 1

    map(matdata[:indexes] |> keys) do key
        L = matdata[:data][key] |> length

        map(matdata[:indexes][key]) do idx
            @match idx begin
                (:idx_neg_1, [i j k]) => (:idx_end, i:k:L)
                (         s, [i -1 k]) => (s, i+1:k:L)
                (         s, [i  j k]) => (s, i+1:k:j+1)
            end
        end |> sort |> OrderedDict
    end |> Dict
end


function load_test_data_raw(name, testspath::String; stage="norm", method="cycles")
    folder = "$testspath/$name"

    # find the files
    trends_file = glob("data/data (*$stage*trends*$method*).mat", folder) |> first;
    tracks_file = glob("data/data (*$stage*tracking*$method*).mat", folder) |> first;

    # read the files
    trends_mat = matread(trends_file);
    tracks_mat = matread(tracks_file);

    return { :info => info, :trends => trends_mat, :tracks => tracks_mat }
end

function simplify_test_data(testdata::Dict)
    Dict( [ symbol(string(k)) => simplify_mat(v) for (k,v) in testdata])
end

function load_test_data(name, tests::String; stage="norm", method="cycles")
    test_data = load_test_data_raw(name, tests) |> simplify_test_data

    trends_slices = mat_slices(test_data[:trends])
    tracks_slices = mat_slices(test_data[:tracks])

    return test_data ∪ {
        :trends => ( test_data[:trends] ∪ {:indexes => trends_slices} ),
        :tracks => ( test_data[:tracks] ∪ {:indexes => tracks_slices} ),
    }
end

function simple_fit(x, y)

    fit = GLM.lm([ones(x) x], y)
    b,a = fit.pp.beta0;

    fit_r2 = r2(y, fit);

    return { :fit => fit, :r2 => fit_r2, :a => a, :b => b, :f => (x -> a*x + b),
        :fstr => "\$$( ff(a,1)) \\,x + $(ff(b,1))\$"  }
end

function r2(ydata, fit)
    1-sumabs2(GLM.residuals(fit))/sumabs2(ydata - mean(ydata)) # or 1-var(residuals(mod))/var(y)
end


## HTML Text ###
th(i) = "<th>$i</th>"
th(s::Array) = map(th, s)
th(s...) = map(th, s)

td(i) = "<td>$i</td>"
td(s::Array) = map(td, s)
td(s...) = map(td, s)

tr(i) = "<tr>$i</tr>"
tr(s::Dict) = [ tr(k)*tr(v) for (k,v) in s ]
tr(s::Array) = map(tr, s)
tr(s...) = map(tr, s)

## Test Helpers ##
join_nt(s) = "\t"*join(s, "\n\t")*"\n"
join_ss(s) = join(s, " ")

maketablerows(s::Array) = tr( [ join( [ td(i) for i in j ], "") for j in s ] ) |> joint_nt

tabulate(s; headers::Array=[]) = HTML("""
<table>
$( isempty(headers) ? "" : tr( [ th(i...) for i in headers] |> join_ss ) |> joint_nt )
$( maketablerows(s) )
</table>
""")

## Data Handling ##

## Research Dir
load_tests_from_md(f::Function, testfile) = load_tests_from_md(testfile, f=f)

function load_tests_from_md(testfile; f::Function=(x)->x)
    tests = open("$testfile") do f readlines(f) end
    headers = tests[1] |> markdownsplitter |> xs->map(lowercase, xs) |> xs->map(symbol, xs)
    @show headers

    @pipe( tests[3:end]
        |> map(markdownsplitter,_)
        |> filter( l -> any(  x -> !isempty(x), l), _)
        |> map(dictFromArray(headers),_)
        |> map(f,_)
    )
end

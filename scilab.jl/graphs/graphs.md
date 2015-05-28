
## Gadfly: Getting Started

[Getting Started](http://dcjones.github.io/Gadfly.jl/)

```julia
	# E.g.
plot(x=1:10, y=2.^rand(10),
     Scale.y_sqrt, Geom.point, Geom.smooth,
     Guide.xlabel("Stimulus"), Guide.ylabel("Response"), Guide.title("Dog Training"))

```

### Drawing to backends


```julia
p = plot(x=[1,2,3], y=[4,5,6])
draw(PNG("myplot.png", 12cm, 6cm), p)
```

## Random Topics

```julia
draw(D3("plot.js", 6inch, 6inch), p)
```

```html
<script src="d3.min.js"></script>
<script src="gadfly.js"></script>

<!-- Placed whereever you want the graphic to be rendered. -->
<div id="my_chart"></div>
<script src="mammals.js"></script>
<script>
draw("#my_chart");
</script>
```



### How to plot two lines with different colors? #526

[How to plot two lines with different colors? #526](https://github.com/dcjones/Gadfly.jl/issues/526)

```julia
plot(layer( x=[1:10], y=rand(10),Geom.point, Geom.line, Theme(default_color=color("orange")) ),
      layer( x=[1:10], y=rand(10),Geom.point, Geom.line, Theme(default_color=color("purple"))) )
```

### Legend for layers with specified colors in Gadfly


[Ability to specify manual color keys #344](https://github.com/dcjones/Gadfly.jl/issues/344)

```julia
plot(x=rand(10), y=rand(10),
     Guide.manual_color_key("Some Title",
                            ["item one", "item two", "item three"],
                            ["red", "green", "blue"]))
```

[Google Groups (OP)](https://groups.google.com/forum/#!topic/julia-users/u99UchCBkSs)
```julia
using Gadfly, DataFrames

	# populate the data in the format from your example
x1 = [1:10]; y1=[12:21]
x2 = [1:10]; y2 = [30:-1:21]

	# make a 3 column DataFrame (x,y,line); maybe not the best way to make a DataFrame, but it works.
df = DataFrame(Dict((:x,:y,:line),([x1,x2],[y1,y2],[["Line 1" for i=1:10],["Line 2" for i=1:10]])))

	# plot the DataFrame
plot(df,x=:x,y=:y,color=:line,Scale.discrete_color_manual("red","purple"),Geom.line,Guide.colorkey("Legend title"))
```

## Comparison: Matplotlib vs Gadfly

```julia
load_max_mean = trends[:data][:load_max][tm_step1half[1]:tm_step1half[2]] |> mean
load_min_mean = trends[:data][:load_min][tm_step1half[1]:tm_step1half[2]] |> mean
println("load_max_mean: $load_max_mean, load_min_mean: $load_min_mean")


	# Matplotlib #
	
p = plot(                                                                                         |  (fig, ax1) = subplots(;ncols=1,nrows=1)
	Guide.xlabel("Time [s]"), Guide.ylabel("Force [N]"), Guide.title("Cycles"),                   |  ax1[:plot](tracking[:data][:totalTime][tm_step[1]:end], tracking[:data][:load][tm_step[1]:end])
	Theme(background_color=color("white")),                                                       |  ax1[:plot](tm_times1[tm_step1[1]:end], trends[:data][:load_max][tm_step1[1]:end])
	layer(                                                                                        |  ax1[:plot](tm_times1[tm_step1[1]:end], trends[:data][:load_min][tm_step1[1]:end])
	    x=tracking[:data][:totalTime][tm_step[1]:end], y=tracking[:data][:load][tm_step[1]:end],  |
		Geom.line, Theme(default_color=color("purple "))                                          |  ax1[:hlines](load_max_mean, tm_times1half[1], tm_times1half[end]; )
	),                                                                                            |  ax1[:hlines](load_min_mean, tm_times1half[1], tm_times1half[end]; )
	layer(                                                                                        |  ax1[:set_ylabel]("Force [N]")
	    x=tm_times1[tm_step1[1]:end], y=trends[:data][:load_max][tm_step1[1]:end],                |  ax1[:set_xlabel]("Time [s]")
		Geom.line, Theme(default_color=color("orange"))                                           |  ax1[:set_title](name)
	),                                                                                            |  fig[:show]()
	layer(                                                                                        |
	    x=tm_times1[tm_step1[1]:end], y=trends[:data][:load_min][tm_step1[1]:end],                |                                                                                                
	    Geom.line, Theme(default_color=color("blue"))                                             | 
	),                                                                                            |
)                                                                                                 |
draw(PNG("myplot.png", 9inch, 6inch, dpi=300), p)                                                 |





pcolors = Dict( [ (symbol(name), Theme(default_color=color(name))) for name in ["purple", "orange", "blue"] ]) 
                                                                                                               
l1=layer(x=tracking[:data][:totalTime][tm_step[1]:end], y=tracking[:data][:load][tm_step[1]:end],              
            Geom.line, pcolors[:purple])                                                                       
l2 = layer(x=tm_times1[tm_step1[1]:end], y=trends[:data][:load_max][tm_step1[1]:end],                          
            Geom.line, pcolors[:orange])                                                                       
l3 = layer(x=tm_times1[tm_step1[1]:end], y=trends[:data][:load_min][tm_step1[1]:end],                          
            Geom.line, pcolors[:blue])                                                                         
plot(                                                                                                          
    Guide.xlabel("Time [s]"), Guide.ylabel("Force [N]"), Guide.title("Cycles"),                                
    Theme(background_color=color("white")),                                                                    
    l1, l2, l3, yintercept=[load_max_mean, load_min_mean], Geom.hline,                                         
)                                                                                                              
draw(PNG("myplot.png", 9inch, 6inch, dpi=100), p)                                                              























```

















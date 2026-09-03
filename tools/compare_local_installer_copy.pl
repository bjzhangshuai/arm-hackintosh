#!/usr/bin/perl
# Read-only, byte-for-byte tree comparison; never follows directory symlinks.
use strict;
use warnings;
my ($original, $copy, $support) = @ARGV;
die "three paths required\n" unless @ARGV == 3 && -d $original && -d $copy;
my ($files, $bytes) = (0, 0);
sub compare_tree {
    my ($relative) = @_;
    my ($a, $b) = ("$original/$relative", "$copy/$relative");
    my @sa = lstat($a); my @sb = lstat($b);
    die "missing path: $relative\n" unless @sa && @sb;
    die "type/mode differs: $relative\n" unless ($sa[2] & 0177777) == ($sb[2] & 0177777);
    if (-l $a) {
        die "symlink differs: $relative\n" unless readlink($a) eq readlink($b);
    } elsif (-d $a) {
        opendir(my $ad, $a) or die "$a: $!";
        opendir(my $bd, $b) or die "$b: $!";
        my @an = sort grep { $_ ne '.' && $_ ne '..' } readdir($ad);
        my @bn = sort grep { $_ ne '.' && $_ ne '..' } readdir($bd);
        closedir($ad); closedir($bd);
        if ($relative eq 'Contents') {
            die "original has SharedSupport\n" if grep { $_ eq 'SharedSupport' } @an;
            die "wrong added SharedSupport\n" unless -l "$b/SharedSupport" && readlink("$b/SharedSupport") eq $support;
            @bn = grep { $_ ne 'SharedSupport' } @bn;
        }
        die "directory entries differ: $relative\n" unless join("\0", @an) eq join("\0", @bn);
        compare_tree(length($relative) ? "$relative/$_" : $_) for @an;
    } elsif (-f $a) {
        die "size differs: $relative\n" unless $sa[7] == $sb[7];
        open(my $af, '<', $a) or die "$a: $!";
        open(my $bf, '<', $b) or die "$b: $!";
        binmode($af); binmode($bf);
        while (1) {
            my ($ab, $bb);
            my $na = read($af, $ab, 65536); my $nb = read($bf, $bb, 65536);
            die "read error: $relative\n" unless defined($na) && defined($nb);
            die "bytes differ: $relative\n" unless $na == $nb && $ab eq $bb;
            last unless $na;
        }
        close($af); close($bf); $files++; $bytes += $sa[7];
    } else { die "unsupported file type: $relative\n"; }
}
compare_tree('');
print "MACVM_LOCAL_APP_BYTE_IDENTITY files=$files bytes=$bytes extra_sharedsupport_symlink=1\n";

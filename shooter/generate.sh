do_generate()
{
	cd "$(dirname "$0")"
	../generate.sh
	mkdir -p orwell/messages
	base="$(dirname "$PWD")"
	for pb in "$base/orwell/messages/"*.py ; do
		ln -nfs "$pb" orwell/messages/
	done
}

do_generate

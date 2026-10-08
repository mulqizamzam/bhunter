import dns.resolver


def enumerate_subdomains(domain, wordlist, resolvers):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = resolvers
    found = []
    with open(wordlist) as f:
        for line in f:
            sub = line.strip()
            if not sub:
                continue
            host = f"{sub}.{domain}"
            try:
                answers = resolver.resolve(host, "A")
                found.append((host, [r.address for r in answers]))
            except (dns.resolver.NXDOMAIN,
                    dns.resolver.NoAnswer,
                    dns.resolver.Timeout):
                continue
    return found

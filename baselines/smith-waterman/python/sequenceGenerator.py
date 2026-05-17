# generate_large_test.py
import random

def generate_dna_sequence(length):
    """Generate random DNA sequence"""
    bases = ['A', 'C', 'G', 'T']
    return ''.join(random.choice(bases) for _ in range(length))

def generate_similar_sequence(template, mutation_rate=0.1, indel_rate=0.05):
    """Generate sequence similar to template with mutations and indels"""
    result = []
    i = 0
    while i < len(template):
        rand = random.random()
        if rand < indel_rate:  # Deletion
            i += 1
        elif rand < 2 * indel_rate:  # Insertion
            result.append(random.choice(['A', 'C', 'G', 'T']))
        elif rand < mutation_rate + 2 * indel_rate:  # Mutation
            bases = ['A', 'C', 'G', 'T']
            bases.remove(template[i])
            result.append(random.choice(bases))
            i += 1
        else:  # Match
            result.append(template[i])
            i += 1
    return ''.join(result)

# Generate test file
if __name__ == "__main__":

    size = 10000

    query = generate_dna_sequence(size)
    reference = generate_similar_sequence(query, mutation_rate=0.15, indel_rate=0.05)
        
    with open(f'large_test_input.txt', 'w') as f:
        f.write(query + '\n')
        f.write(reference + '\n')
    print("Test files generated successfully!")
from django.core.management.base import BaseCommand
from api.util import build_enhanced_vector_index
import time

class Command(BaseCommand):
    help = 'Rebuild the enhanced FAISS vector index'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force rebuild even if index exists')

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write("🔄 Rebuilding enhanced FAISS vector index...")
        
        try:
            start_time = time.time()
            build_enhanced_vector_index()
            elapsed = time.time() - start_time
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Enhanced vector index rebuilt successfully in {elapsed:.2f} seconds"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to rebuild index: {str(e)}")
            )
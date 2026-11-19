<?php

namespace Tests\Feature;

use App\Http\V1\Controllers\HelpController;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;

/**
 * GET /api/V1/documentation: the platform manual, streamed from the bucket. The bucket is faked;
 * no database is needed.
 */
class DocumentationDownloadTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('s3');
    }

    public function test_it_downloads_the_manual_as_a_pdf_attachment_without_a_session(): void
    {
        Storage::disk('s3')->put(HelpController::MANUAL_PATH, '%PDF-1.7 manual');

        $response = $this->get('/api/V1/documentation');

        $response->assertOk();
        $response->assertHeader('Content-Type', 'application/pdf');
        $this->assertStringContainsString('attachment', $response->headers->get('Content-Disposition'));
        $this->assertStringContainsString('manual-plataforma.pdf', $response->headers->get('Content-Disposition'));
        $this->assertSame('%PDF-1.7 manual', $response->streamedContent());
    }

    public function test_it_answers_404_while_the_manual_has_not_been_uploaded(): void
    {
        Storage::disk('s3')->put('documentation/otro-documento.pdf', '%PDF-1.7 otro');

        $this->get('/api/V1/documentation')->assertNotFound();
    }

    public function test_the_old_per_language_route_is_gone(): void
    {
        Storage::disk('s3')->put(HelpController::MANUAL_PATH, '%PDF-1.7 manual');

        $this->get('/api/V1/documentation/es')->assertNotFound();
    }
}

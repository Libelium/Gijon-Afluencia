<?php

namespace App\Http\V1\Resources;

use Illuminate\Support\Facades\Storage;

class DashboardResource extends \App\Http\V1\Resources\DefaultPermissionsResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'description' => $this->description,
            'slug' => $this->slug,
            'type' => $this->type,
            'timezone' => $this->timezone,
            'layout' => $this->layout,
            'user_id' => $this->user_id,
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,
            'templateDrawer' => $this->template_type,
            'config' => $this->config,
            'entities' => isset($this->entities) ? EntityResource::collection($this->entities) : [],
            'devices' => isset($this->devices) ? DeviceFullResource::collection($this->devices) : [],
            'groups' => isset($this->groups) ? EntityGroupResource::collection($this->groups) : [],
            'panels' => isset($this->panels) ? PanelResource::collection($this->panels) : [],
            'regulation' => isset($this->regulation) ? new RegulationResource($this->regulation) : null,
            'dateRange' => isset($this->date_range) ? json_decode($this->date_range) : null,
            'viewMode' => $this->view_mode,
            'hidden' => (bool) $this->hidden,
            'publicViewIcon' => isset($this->public_view_icon) ? $this->public_view_icon : null,
            'publicViewDarkIcon' => isset($this->public_view_dark_icon) ? $this->public_view_dark_icon : null,
            'creatorPreferences' => isset($this->creator_preferences) ? $this->creator_preferences : null,
            'tags' => TagResource::collection($this->whenLoaded('tags')),
            'previewImage' => $this->preview_image ?? null,
            'previewImageUrl' => $this->getPreviewImageUrl(),
        ];
    }

    /**
     * Get temporary URL for preview image if it exists
     *
     * @return string|null
     */
    protected function getPreviewImageUrl(): ?string
    {
        if (!$this->preview_image || !str_starts_with($this->preview_image, 'org_')) {
            return null;
        }

        $basePath = config('filesystems.paths.dashboard_images');
        $path = $basePath . '/' . $this->preview_image;

        $exists = Storage::disk('s3')->exists($path);

        if (!$exists) {
            return null;
        }

        return Storage::disk('s3')->temporaryUrl($path, now()->addMinutes(15));
    }
}

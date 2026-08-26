<?php

namespace App\Services\UserDeletion;

use App\Contracts\UserResourceHandlerInterface;
use App\Contracts\DeletableWithUserInterface;

class TransferableRegistry
{
    /** @var array<array{handler: class-string<UserResourceHandlerInterface>, model: class-string|null}> */
    private array $transferable = [];

    /** @var array<array{handler: class-string<DeletableWithUserInterface>, model: class-string|null}> */
    private array $deletable = [];

    /**
     * @param class-string<UserResourceHandlerInterface> $handlerClass
     * @param class-string|null $modelClass
     */
    public function registerTransferable(string $handlerClass, ?string $modelClass = null): self
    {
        $this->transferable[] = ['handler' => $handlerClass, 'model' => $modelClass];
        return $this;
    }

    /**
     * @param class-string<DeletableWithUserInterface> $handlerClass
     * @param class-string|null $modelClass
     */
    public function registerDeletable(string $handlerClass, ?string $modelClass = null): self
    {
        $this->deletable[] = ['handler' => $handlerClass, 'model' => $modelClass];
        return $this;
    }

    /** @return array<array{handler: class-string<UserResourceHandlerInterface>, model: class-string|null}> */
    public function getTransferable(): array
    {
        return $this->transferable;
    }

    /** @return array<array{handler: class-string<DeletableWithUserInterface>, model: class-string|null}> */
    public function getDeletable(): array
    {
        return $this->deletable;
    }
}
